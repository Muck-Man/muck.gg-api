from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import Permissions

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/users/{uid}'
		self.types = {'uid': 'snowflake'}
	
	async def get(self, request, uid):
		user = await self.server.tools.authorize(
			request.headers.get('Authorization'),
			bot_permissions=['OWNER']
		)

		if uid == '@me':
			if user['bot']:
				if not user.get('user'):
					raise InvalidUsage(400, 'Cannot use @me with bots without specifying user id in the token')
				
				uid = user['user']['id']
			else:
				uid = user['id']
		
		if uid != user.get('user', user)['id'] and not Permissions.check_any(user.get('user', user)['permissions'], ['OWNER', 'SUPERADMIN', 'ADMIN']):
			raise InvalidUsage(401)

		requested = {}
		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				if user['bot'] and user.get('user', None) and uid == user['user']['id']:
					requested.update(user['user'])
				elif not user['bot'] and uid == user['id']:
					requested.update({
						'id': user['id'],
						'username': user['username'],
						'discriminator': user['discriminator'],
						'avatar_hash': user['avatar_hash'],
						'refreshed': user['refreshed'],
						'permissions': user['permissions']
					})
				else:
					await cur.execute('SELECT * FROM `users` WHERE `id` = %s', (uid,))
					requested.update(await cur.fetchone())
				
				#update information from discord if not requested from bot
		finally:
			self.server.database.release(connection)
		
		if not requested:
			raise InvalidUsage(404, 'User not found')
		else:
			requested['discriminator'] = '{:04}'.format(requested['discriminator'])
			return Response(200, requested)