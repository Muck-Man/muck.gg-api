from decimal import *

import datetime
import hashlib
import time

from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import IdTypes, Permissions, PerspectiveAttributes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck'

		self.perspective = self.server.config.get('googleapi', {}).get('perspective', None)

		self.attributes = {k.name: {} for k in PerspectiveAttributes}
	
	async def average(self, timestamp, guild_id, channel_id, user_id, scores):
		started = timestamp
		timestamp = datetime.date.fromtimestamp(timestamp) - datetime.timedelta(1)
		timestamp = timestamp.strftime('%s')

		scores = {attribute.value: scores[attribute.value] for attribute in PerspectiveAttributes}
		kscores = list(scores.keys())
		vscores = list(scores.values())

		values = [
			[started, 0, 0, 0, 0],
			[started, 0, guild_id, 0, 0] if guild_id else None,
			[started, 0, 0, channel_id, 0],
			[started, 0, 0, 0, user_id],
			[started, 0, guild_id, 0, user_id] if guild_id else None,
			[started, 0, 0, channel_id, user_id],
			[started, timestamp, 0, 0, 0],
			[started, timestamp, guild_id, 0, 0] if guild_id else None,
			[started, timestamp, 0, channel_id, 0],
			[started, timestamp, 0, 0, user_id],
			[started, timestamp, guild_id, 0, user_id] if guild_id else None,
			[started, timestamp, 0, channel_id, user_id]
		]
		values = [v + [1] + vscores for v in values if v is not None]

		keys = ['started', 'timestamp', 'guild_id', 'channel_id', 'user_id', 'count'] + kscores
		statement = ' '.join([
			'INSERT INTO  `muck_averages`',
			'({})'.format(', '.join(['`{}`'.format(k) for k in keys])),
			'VALUES',
			', '.join([
				'({})'.format(', '.join(['%s' for a in range(len(keys))])) for i in range(len(values))
			]),
			'ON DUPLICATE KEY UPDATE',
			', '.join([
				', '.join(['`{k}` = ROUND(`{k}` + VALUES(`{k}`), 10)'.format(k=k) for k in kscores]),
				'`count` = `count` + VALUES(`count`)'
			])
		])

		#store 0 0 0 0 (global since start)
		#-------------------------------------
		#store 0 guild_id 0 0 (guild stats from start)
		#store 0 0 channel_id 0 (channel stats from start)
		#store 0 0 0 user_id (user stats from start)
		#-------------------------------------
		#store timestamp 0 0 0 (global for 1 day)
		#store timestamp guild_id 0 0 (specific for 1 day) (to get guild stats for the day)
		#store timestamp 0 channel_id 0 (specific for 1 day) (to get channel stats for the day)
		#store timestamp guild_id channel_id user_id (specific for 1 day) (to get user stats for the day (guild/channel specific or average of everything for the day since they can only talk in 100 guilds))

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute(
					statement,
					[x for y in values for x in y]
				)
		except Exception as e:
			print(e)
		finally:
			self.server.database.release(connection)

	async def post(self, request):
		bot = await self.server.tools.authorize(
			request.headers.get('Authorization'),
			bots=True
		)

		if not self.perspective:
			raise InvalidUsage(500, 'Server missing perspective API key')
		
		#store = bool(request.query.get('store', None) == 'true')
		store = not bool(request.query.get('store', None) == 'false')

		data = self.validate(await request.json(), required=['content'])
		if store:
			if not Permissions.check(bot['permissions'], 'OWNER'):
				raise InvalidUsage(401)
			data = self.validate(data, required=['message_id', 'channel_id', 'user_id', 'timestamp'])
			data['guild_id'] = data.get('guild_id', None)
			if data['guild_id'] == 'null':
				data['guild_id'] = None
			data['edited'] = bool(data.get('edited', False))
		
		if not data['content']:
			#if they send in a blank content lol
			raise InvalidUsage(400)

		mhash = hashlib.sha256(data['content'].encode()).hexdigest()

		response = {}
		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				if store:
					if await cur.execute('SELECT * FROM `muck_messages` WHERE `message_id` = %s AND `timestamp` = %s AND `edited` = %s', (data['message_id'], data['timestamp'], data['edited'])):
						raise InvalidUsage(400, 'Message already inside database.')

				await cur.execute('SELECT * FROM `muck_cache` WHERE `hash` = %s', (mhash,))
				scores = await cur.fetchone()

				if not scores or scores['analyzed'] < int(time.time() - 86400):
					response = await self.server.httpclient.googleapi_perspective(self.perspective['token'], data['content'], self.attributes, True)
					if response['status'] != 200:
						if not response['json']:
							raise InvalidUsage(response['status'], 'Google\'s API errored out with this status.')
						else:
							raise InvalidUsage(response['status'], response['data']['error']['message'])
					response = response['data']

					if scores:
						scores = {}
					else:
						scores = {'hash': mhash}

					for key in response['attributeScores'].keys():
						scores[key.lower()] = round(response['attributeScores'][key]['summaryScore']['value'], 7)
					
					scores['analyzed'] = int(time.time())
					
					iscores = scores.items()
					if scores.get('hash', None):
						await cur.execute(
							'INSERT INTO `muck_cache` ' +
							'({}) '.format(', '.join(['`{}`'.format(k) for k, v in iscores])) +
							'VALUES ' +
							'({})'.format(', '.join(['%s' for k, v in iscores])),
							[v for k, v in iscores]
						)
					else:
						await cur.execute(
							' '.join([
								'UPDATE `muck_cache` SET',
								', '.join(
									['`{}` = %s'.format(k) for k, v in iscores]
								),
								'WHERE `hash` = %s'
							]),
							[v for k, v in iscores] + [mhash]
						)
				
				response['hash'] = scores.pop('hash')
				response['analyzed'] = scores.pop('analyzed')
				response['scores'] = scores

				if store:
					await cur.execute(
						'INSERT INTO `muck_messages` (`message_id`, `guild_id`, `channel_id`, `user_id`, `hash`, `timestamp`, `edited`) VALUES (%s, %s, %s, %s, %s, %s, %s)',
						(data['message_id'], data['guild_id'], data['channel_id'], data['user_id'], mhash, data['timestamp'], data['edited'])
					)

					self.server.loop.create_task(self.average(data['timestamp'], data['guild_id'], data['channel_id'], data['user_id'], scores))
		finally:
			self.server.database.release(connection)
		
		return Response(200, response)
