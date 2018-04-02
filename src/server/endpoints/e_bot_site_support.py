from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.redirect import Redirect

class RestEndpoint(Endpoint):
    def __init__(self, server):
        super().__init__()
        self.server = server
        self.path = '/bot/{site}/support'
    
    async def site_discord(self, request):
        return Redirect(302, 'https://discord.gg/kcPjgg3')
    
    async def get(self, request, site):
        method = getattr(self, 'site_{}'.format(site))
        if not method:
            raise InvalidUsage(400, 'Invalid Oauth2 Site')
        return await method(request)