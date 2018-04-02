from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.redirect import Redirect

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/bot/{site}/oauth2'

		self.oauth2 = self.server.config.get('oauth2')

	async def site_discord(self, request, session):
		if not self.oauth2.get('discord'):
			raise InvalidUsage(500, 'Server missing Discord oauth2 config')

		params = {
			'scope': 'identify guilds',
			'response_type': 'code',
			'client_id': self.oauth2['discord'].get('id'),
			'state': self.server.snowflake.generate(),
			'redirect_uri': self.oauth2['discord'].get('redirect_uri')
		}

		session['state'] = params['state']

		return Redirect(302, 'https://discordapp.com/api/oauth2/authorize', params)

	async def get(self, request, site):
		method = getattr(self, 'site_{}'.format(site))
		if not method:
			raise InvalidUsage(404, 'oauth2 type not supported')
		
		session = await self.server.router.get_session(request)
		return await method(request, session)