from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/auth/login'
	
	async def post(self, request):
		try:
			data = self.validate(await request.json())
			token = self.server.token.split(data.get('token', None))
		except:
			raise InvalidUsage(400)
		
		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute('SELECT * FROM `token_states` WHERE `id` = %s', (token['user_id'],))
				state = await cur.fetchone()
				if not state or not self.server.token.compare(token['hmac'], state['snowflake'], state['secret']):
					raise InvalidUsage(400)
				
				await cur.execute('SELECT `id` FROM `users` WHERE `id` = %s', state['user_id'])
				user = await cur.fetchone()
				if not user:
					raise InvalidUsage(500, 'lol no user found')
				
				session_token = self.server.token.generate(user['id'])
				await cur.execute(
					'INSERT INTO `token_sessions` (`id`, `user_id`, `secret`, `last_used`) VALUES (%s, %s, %s, %s)',
					(session_token['snowflake'], user['id'], session_token['secret'], 0)
				)
				await cur.execute('DELETE FROM `token_states` WHERE `id` = %s', (token['user_id'],))
		finally:
			self.server.database.release(connection)

		if session_token:
			return Response(200, {'token': session_token['token']})
		else:
			raise InvalidUsage(400)