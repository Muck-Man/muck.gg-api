import time

from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.redirect import Redirect

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/bot/{site}/oauth2/callback'

		self.oauth2 = self.server.config.get('oauth2')
	
	async def site_discord(self, request, session):
		if not self.oauth2.get('discord'):
			raise InvalidUsage(500, 'Server missing Discord Oauth2 Config')

		server_state = session.get('state')
		if not server_state or not request.query.get('state') or int(server_state) != int(request.query.get('state')):
			raise InvalidUsage(400, 'Invalid State')
		
		if request.query.get('error'):
			raise InvalidUsage(400, request.query['error'])
		if not request.query.get('code'):
			raise InvalidUsage(400, 'Missing Code')

		response = await self.server.httpclient.discord_post_oauth2_token(
			client_id=self.oauth2['discord'].get('id'),
			client_secret=self.oauth2['discord'].get('secret'),
			grant_type='authorization_code',
			code=request.query.get('code'),
			redirect_uri=self.oauth2['discord'].get('redirect_uri')
		)

		if response['status'] != 200:
			if response['json']:
				raise InvalidUsage(response['status'], response['data']['error'])
			else:
				raise InvalidUsage(500, 'Discord API Error')
		response = response['data']

		scope = response.get('scope', '').split(' ')
		if 'identify' not in scope or 'guilds' not in scope:
			raise InvalidUsage(400, 'Missing Identify or Guilds in scope.')
		
		oauth2 = {
			'scope': response['scope'],
			'token_type': response['token_type'],
			'access_token': response['access_token'],
			'refresh_token': response['refresh_token'],
			'expires_in': response['expires_in'],
			'refreshed': int(time.time())
		}

		token = '{} {}'.format(oauth2['token_type'], oauth2['access_token'])

		response = await self.server.httpclient.discord_get_users_me(token)
		if response['status'] != 200:
			if response['json']:
				raise InvalidUsage(response['data']['code'], response['data']['message'])
			else:
				raise InvalidUsage(500, 'Discord API Error')
		response = response['data']

		user = {
			'id': response['id'],
			'username': response['username'],
			'discriminator': int(response['discriminator']),
			'avatar_hash': response['avatar'],
			'refreshed': int(time.time())
		}

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				if (await cur.execute('SELECT * FROM `users` WHERE `id` = %s', (user['id'],))):
					old = await cur.fetchone()

					iuser = user.items()
					await cur.execute(
						'UPDATE `oauth2` SET ' +
						'{} '.format(', '.join(['`{}` = {}'.format(k, '%s') for k, v in iuser])) +
						'WHERE `id` = %s',
						[v for k, v in iuser] + [user['id']]
					)

					ioauth2 = oauth2.items()
					await cur.execute(
						'UPDATE `oauth2` SET ' +
						'{} '.format(', '.join(['`{}` = {}'.format(k, '%s') for k, v in ioauth2])) +
						'WHERE `user_id` = %s',
						[v for k, v in ioauth2] + [user['id']]
					)
				else:
					oauth2['user_id'] = user['id']

					iuser = user.items()
					ioauth2 = oauth2.items()
					await cur.execute(
						'INSERT INTO `users` ' +
						'({}) '.format(', '.join(['`{}`'.format(k) for k, v in iuser])) +
						'VALUES ' +
						'({})'.format(', '.join(['%s' for k, v in iuser])),
						[v for k, v in iuser]
					)
					await cur.execute(
						'INSERT INTO `oauth2` ' +
						'({}) '.format(', '.join(['`{}`'.format(k) for k, v in ioauth2])) +
						'VALUES ' +
						'({})'.format(', '.join(['%s' for k, v in ioauth2])),
						[v for k, v in ioauth2]
					)
		except Exception as roof:
			self.server.database.release(connection)
			raise roof

		return (user['id'], server_state, connection)
	
	async def get(self, request, site):
		if not self.oauth2.get('token_uri'):
			raise InvalidUsage(500, 'Site not configured properly')

		if site == 'token_uri':
			raise InvalidUsage(404)

		session = await self.server.router.get_session(request)
		method = getattr(self, 'site_{}'.format(site))
		if not method:
			raise InvalidUsage(404, 'oauth2 type not supported')

		user_id, state_id, connection = await method(request, session)
		state_token = self.server.token.generate(state_id)

		async with connection.cursor() as cur:
			await cur.execute(
				'INSERT INTO `token_states` (id, user_id, snowflake, secret) VALUES (%s, %s, %s, %s)',
				(state_id, user_id, state_token['snowflake'], state_token['secret'])
			)
		self.server.database.release(connection)

		return Redirect(302, self.oauth2.get('token_uri'), params={'token': state_token['token']})