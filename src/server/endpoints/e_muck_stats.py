import datetime

from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import IdTypes, PerspectiveAttributes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck/stats'

		self.id_types = {
			'GUILDS': 'guild_id',
			'CHANNELS': 'channel_id',
			'USERS': 'user_id'
		}
	
	async def get(self, request):
		data = {
			'timestamp': datetime.date.today() - datetime.timedelta(1),
			'scores': [
				{'type': 'guilds', 'data': {}},
				{'type': 'channels', 'data': {}}
			]
		}
		data['timestamp'] = data['timestamp'].strftime('%s')

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				for score in data['scores']:
					id_type = self.id_types.get(score['type'].upper(), None)
					if not id_type:
						continue
					
					where = ['`inserted` >= %s']

					if id_type == 'guild_id':
						where.append('`guild_id` is not null')
					
					await cur.execute(
						' '.join([
							'SELECT',
							'{}'.format(
								', '.join(
									['AVG(`muck_cache`.`{a}`) AS "{a}"'.format(a=attribute.value) for attribute in PerspectiveAttributes] +
									['COUNT(*) AS "count"']
								)
							),
							'FROM `muck_messages`',
							'INNER JOIN `muck_cache` ON `muck_messages`.`hash` = `muck_cache`.`hash`',
							'WHERE',
							' AND '.join(where),
						]),
						(data['timestamp'],)
					)

					score['data'].update(await cur.fetchone())
		finally:
			self.server.database.release(connection)

		'''
		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				for idt in scores.keys():
					id_type = IdTypes.get(idt.upper())

					await cur.execute(
						' '.join([
							'SELECT',
							'{}'.format(
								', '.join(
									['AVG(`{a}`) AS "{a}"'.format(a=attribute) for attribute in self.attributes] +
									['AVG(`unique_{a}`) AS "unique_{a}"'.format(a=attribute) for attribute in self.attributes] +
									['SUM(`count`) AS `count`', 'SUM(`unique_count`) AS `unique_count`']
								)
							),
							'FROM `muck_averages` WHERE `id_type` = %s'
						]),
						(id_type.value,)
					)
					score = await cur.fetchone()
					scores[idt]['duplicates'] = {k: float(score[k]) for k in self.attributes}
					scores[idt]['duplicates']['count'] = score['count']
					scores[idt]['unique'] = {k: float(score['unique_{}'.format(k)]) for k in self.attributes}
					scores[idt]['unique']['count'] = score['unique_count']
		finally:
			self.server.database.release(connection)
		
		'''
		
		return Response(200, data)
