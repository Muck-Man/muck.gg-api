import datetime

from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import IdTypes, PerspectiveAttributes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck/stats/{idtype}/{sid}'

		self.types = {'id': 'snowflake'}

		self.id_types = {
			'GUILDS': 'guild_id',
			'CHANNELS': 'channel_id',
			'USERS': 'user_id'
		}
	
	async def get(self, request, idtype, sid):
		idtype = IdTypes.get(idtype.upper())
		if not idtype:
			raise InvalidUsage(404)
		
		idt = self.id_types.get(idtype.name)
		
		data = {
			'timestamp': datetime.date.today() - datetime.timedelta(1),
			'score': {}
		}
		data['timestamp'] = data['timestamp'].strftime('%s')

		where = [
			'`inserted` >= %s',
			'`{}` = %s'.format(idt)
		]

		values = [data['timestamp'], sid]

		if idt == 'user_id':
			if request.query.get('channel_id', None):
				where.append('`channel_id` = %s')
				values.append(request.query['channel_id'])
			
			if request.query.get('guild_id', None):
				where.append('`guild_id` = %s')
				values.append(request.query['guild_id'])
		
		print(where, values)

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute(
					' '.join([
						'SELECT',
						'{}'.format(
							'{}'.format(
								', '.join(
									['AVG(`muck_cache`.`{a}`) AS "{a}"'.format(a=attribute.value) for attribute in PerspectiveAttributes] +
									['COUNT(*) AS "count"']
								)
							),
						),
						'FROM `muck_messages`',
						'INNER JOIN `muck_cache` ON `muck_messages`.`hash` = `muck_cache`.`hash`',
						'WHERE',
						' AND '.join(where)
					]),
					values
				)
				data['score'].update(await cur.fetchone())
		finally:
			self.server.database.release(connection)
		
		return Response(200, data)
