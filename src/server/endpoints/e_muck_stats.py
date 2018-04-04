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
	
	async def get(self, request):
		#implement using timestamp
		scores = {}

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute(' '.join([
					'SELECT',
					', '.join([
						'`count`',
						', '.join(['`{}`'.format(attribute.value) for attribute in PerspectiveAttributes])
					]),
					'FROM `muck_averages` WHERE `timestamp` = 0 AND `guild_id` = 0 AND `channel_id` = 0 AND `user_id` = 0'
				]))
				scores.update(await cur.fetchone())
		finally:
			self.server.database.release(connection)
		
		return Response(200, scores)
