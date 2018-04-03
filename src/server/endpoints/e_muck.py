from decimal import *

import hashlib
import time

from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import IdTypes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck'

		self.perspective = self.server.config.get('googleapi', {}).get('perspective', None)

		self.attributes = {
			'ATTACK_ON_AUTHOR': {},
			'ATTACK_ON_COMMENTER': {},
			'INCOHERENT': {},
			'INFLAMMATORY': {},
			'LIKELY_TO_REJECT': {},
			'OBSCENE': {},
			'SEVERE_TOXICITY': {},
			'SPAM': {},
			'TOXICITY': {},
			'UNSUBSTANTIAL': {}
		}

		self.idts = {
			'GUILDS': 'guild_id',
			'CHANNELS': 'channel_id',
			'USERS': 'user_id'
		}
	
	async def average(self, cursor, ids, scores):
		attributes = [key.lower() for key in self.attributes.keys()]

		for id_type in ids.keys():
			if not ids[id_type]:
				continue
			id_type = IdTypes.get(id_type)

			idt = self.idts.get(id_type.name)

			unique = True
			await cursor.execute('SELECT COUNT(*) AS "count" FROM `muck_messages` WHERE `{idt}` = %s AND `hash` = %s'.format(idt=idt), (ids[id_type.name], scores['hash']))
			messages = await cursor.fetchone()
			if messages['count'] > 1:
				unique = False
			
			if await cursor.execute('SELECT * FROM `muck_averages` WHERE `id_type` = %s AND `id` = %s', (id_type.value, ids[id_type.name])):
				update = {
					'set': [],
					'values': []
				}
				update['set'] += [
					'{}'.format(', '.join(['`{k}` = ROUND(((`{k}` * `count`) + %s) / (`count` + 1), 7)'.format(k=k) for k in attributes])),
					'`count` = `count` + 1'
				]
				for attribute in attributes:
					update['values'].append(scores[attribute])

				if unique:
					update['set'] += [
						'{}'.format(', '.join(['`unique_{k}` = ROUND(((`unique_{k}` * `unique_count`) + %s) / (`unique_count` + 1), 7)'.format(k=k) for k in attributes])),
						'`unique_count` = `unique_count` + 1'
					]
					for attribute in attributes:
						update['values'].append(scores[attribute])

				await cursor.execute(
					' '.join([
						'UPDATE `muck_averages` SET',
						', '.join(update['set']),
						'WHERE `id_type` = %s AND `id` = %s'
					]),
					update['values'] + [id_type.value, ids[id_type.name]]
				)
			else:
				insert = {
					'columns': ['id_type', 'id'] + attributes + ['count'] + ['unique_{}'.format(a) for a in attributes] + ['unique_count'],
					'values': [id_type.value, ids[id_type.name]] + [scores[a] for a in attributes] + [1] + [scores[a] if unique else 0 for a in attributes] + [1 if unique else 0]
				}

				await cursor.execute(
					' '.join([
						'INSERT INTO `muck_averages`'
						'({})'.format(', '.join(['`{}`'.format(k) for k in insert['columns']])),
						'VALUES',
						'({})'.format(', '.join(['%s' for k in insert['columns']]))
					]),
					insert['values']
				)
	async def post(self, request):
		bot = await self.server.tools.authorize(
			request.headers.get('Authorization'),
			bots=True
		)

		if not self.perspective:
			raise InvalidUsage(500, 'Server missing perspective API key')
		
		data = self.validate(await request.json(), required=['channel_id', 'user_id', 'content', 'is_edit'])
		data['guild_id'] = data.get('guild_id', None)

		mhash = hashlib.sha256(data['content'].encode()).hexdigest()

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				if await cur.execute('SELECT * FROM `muck_cache` WHERE `hash` = %s', (mhash,)):
					scores = await cur.fetchone()
				else:
					scores = {'hash': mhash}
					response = await self.server.httpclient.googleapi_perspective(self.perspective['token'], data['content'], self.attributes, True)
					if response['status'] != 200:
						if not response['json']:
							raise InvalidUsage(response['status'], 'Google\'s API errored out with this status.')
						else:
							raise InvalidUsage(response['status'], response['data']['error']['message'])
					response = response['data']

					for key in response['attributeScores'].keys():
						scores[key.lower()] = round(response['attributeScores'][key]['summaryScore']['value'], 7)
					
					iscores = scores.items()
					await cur.execute(
						'INSERT INTO `muck_cache` ' +
						'({}) '.format(', '.join(['`{}`'.format(k) for k, v in iscores])) +
						'VALUES ' +
						'({})'.format(', '.join(['%s' for k, v in iscores])),
						[v for k, v in iscores]
					)

				await cur.execute(
					'INSERT INTO `muck_messages` (`guild_id`, `channel_id`, `user_id`, `timestamp`, `hash`, `is_edit`) VALUES (%s, %s, %s, %s, %s, %s)',
					(data['guild_id'], data['channel_id'], data['user_id'], time.time(), scores['hash'], data['is_edit'])
				)

				await self.average(cur, {
					'GUILDS': data['guild_id'],
					'CHANNELS': data['channel_id'],
					'USERS': data['user_id']
				}, scores)
		finally:
			self.server.database.release(connection)
		
		return Response(200, scores)
