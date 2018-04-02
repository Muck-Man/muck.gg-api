from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/bot/{site}/commands'
		
		self.oauth2 = self.server.config.get('oauth2')
	
	async def site_discord(self, request):
		return Response(200, {
			'prefixes': ['.m', '.muck'],
			'commands': []
		})
	
	async def get(self, request, site):
		method = getattr(self, 'site_{}'.format(site))
		if not method:
			raise InvalidUsage(404)
		return await method(request)