from server.rest.endpoint import Endpoint
from server.rest.response import Response

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/bots/{bid}'
		self.types = {'bid': 'snowflake'}
	
	async def get(self, request, bid):
		return Response(200, [])