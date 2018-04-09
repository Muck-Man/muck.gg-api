import datetime

from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import ContextTypes, PerspectiveAttributes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck/stats/{itype}/{sid}'

		self.types = {'sid': 'snowflake'}

		self.allowed_types = ['users', 'guilds', 'channels']
	
	async def get(self, request, itype, sid):
		if itype not in self.allowed_types:
			raise InvalidUsage(404)
		

		where = ['`timestamp` = %s']
		values = [0]

		if itype == 'guilds':
			where.append('`context_type` = %s')
			values.append(ContextTypes.GUILDS.value)
			
			where.append('`context_id` = %s')
			values.append(sid)
		elif itype == 'channels':
			where.append('`context_type` = %s')
			values.append(ContextTypes.CHANNELS.value)

			where.append('`context_id` = %s')
			values.append(sid)
		elif itype == 'users':
			where.append('`user_id` = %s')
			values.append(sid)

			context_id = request.query.get('context_id', None)
			context_type = request.query.get('context_type', None)

			if context_id is None or context_type is None:
				if context_id is None and context_type is None:
					context_id = 0
					context_type = ContextTypes.GLOBAL
				else:
					raise InvalidUsage(400, 'Context id and type cannot both be empty when one is passed in.')
			else:
				context_type = ContextTypes.get(context_type.upper())
				if not context_type:
					raise InvalidUsage(400, 'Invalid Context Type')
			
			where.append('`context_type` = %s')
			values.append(context_type.value)

			where.append('`context_id` = %s')
			values.append(context_id)
		
		response = {}
		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute(
					' '.join([
						'SELECT',
						', '.join([
							'`count`',
							'`started`',
							', '.join([
								'`{}`'.format(attribute.value) for attribute in PerspectiveAttributes
							])
						]),
						'FROM `muck_averages` WHERE',
						' AND '.join(where)
					]),
					values
				)

				response['scores'] = await cur.fetchone()
				if not response['scores']:
					raise InvalidUsage(404, 'No data found')
				
				response['count'] = response['scores'].pop('count')
				response['started'] = response['scores'].pop('started')
				for key in response['scores'].keys():
					response['scores'][key] = round(float(response['scores'][key]) / response['count'], 10)
		finally:
			self.server.database.release(connection)
		
		return Response(200, response)
