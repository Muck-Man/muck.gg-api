import datetime

from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import ContextTypes, PerspectiveAttributes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck/stats'
	
	async def get(self, request):
		#implement using timestamp
		data = {}

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
						'`timestamp` = %s AND `context_type` = %s AND `context_id` = %s AND `user_id` = %s'
					]),
					[0, ContextTypes.GLOBAL.value, 0, 0]
				)
				data['scores'] = await cur.fetchone()
				if not data['scores']:
					raise InvalidUsage(404, 'No data found')
				
				data['count'] = data['scores'].pop('count')
				data['started'] = data['scores'].pop('started')
				for key in data['scores'].keys():
					data['scores'][key] = round(float(data['scores'][key]) / data['count'], 10)
		finally:
			self.server.database.release(connection)
		
		return Response(200, data)
