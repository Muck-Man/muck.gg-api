from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.redirect import Redirect

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/bot/{site}/invite'
		
		self.oauth2 = self.server.config.get('oauth2')
	
	async def site_discord(self, request):
		if not self.oauth2.get('discord'):
			raise InvalidUsage(500, 'Server missing Discord Oauth2 Config')
		
		return Redirect(302, 'https://discordapp.com/oauth2/authorize', params={
			'scope': 'bot',
			'client_id': self.oauth2.get('discord').get('id')
		})
	
	async def get(self, request, site):
		method = getattr(self, 'site_{}'.format(site))
		if not method:
			raise InvalidUsage(404)
		return await method(request)