from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/auth/logout'
	
	async def get(self, request):
		user = await self.server.tools.authorize(request.headers.get('Authorization'))
		if user['bot']:
			raise InvalidUsage(401, 'Bots cannot use this endpoint.')

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute('DELETE FROM `token_sessions` WHERE `id` = %s', (user['token']['snowflake'],))
		finally:
			self.server.database.release(connection)

		return Response(204)