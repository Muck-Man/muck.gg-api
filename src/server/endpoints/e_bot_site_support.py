from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.redirect import Redirect

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/bot/{site}/support'

		self.oauth2 = self.server.config.get('oauth2')
	
	async def site_discord(self, request):
		if not self.oauth2.get('discord', None):
			raise InvalidUsage(500, 'Discord link not set up')
		return Redirect(302, self.oauth2['discord'].get('invite'))
	
	async def site_github(self, request):
		if not self.oauth2.get('github', None):
			raise InvalidUsage(500, 'Github link not set up')

		return Redirect(302, self.oauth2['github'].get('url'))
	
	async def get(self, request, site):
		method = getattr(self, 'site_{}'.format(site))
		if not method:
			raise InvalidUsage(404, 'Invalid Oauth2 Site')
		return await method(request)