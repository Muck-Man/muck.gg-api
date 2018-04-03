from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/bots'
	
	async def post(self, request):
		user = await self.server.tools.authorize(
			request.headers.get('Authorization'),
			permissions=['OWNER'],
			bots=False
		)
		
		data = self.validate(await request.json(), required=['name'])

		if len(data['name']) > 32:
			raise InvalidUsage(400, 'Bot name too long')

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute('SELECT * FROM `bots` WHERE `name` = %s', (data['name'],))
				if await cur.fetchone():
					raise InvalidUsage(400, 'Bot name in use')
				
				bid = self.server.snowflake.generate()
				token = self.server.token.generate(bid)

				await cur.execute(
					'INSERT INTO `bots` (`id`, `name`, `permissions`, `snowflake`, `secret`) VALUES (%s, %s, %s, %s, %s)',
					(bid, data['name'], 0, token['snowflake'], token['secret'])
				)
		finally:
			self.server.database.release(connection)

		return Response(200, {'token': token['token']})