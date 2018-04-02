import asyncio
import time

import server.endpoints as endpoints
from server.rest.router import Router

from server.database import Database
from server.httpclient import HTTPClient
from server.snowflake import SnowflakeGenerator
from server.token import TokenGenerator
from server.tools import Tools

class Server:
	def __init__(self, **kwargs):
		self.loop = kwargs.pop('loop', asyncio.get_event_loop())
		self.host = kwargs.pop('host', '127.0.0.1')
		self.port = kwargs.pop('port', 8000)
		self.cloudflare = kwargs.pop('cloudflare', False)

		self.snowflake = SnowflakeGenerator(**kwargs.pop('snowflake', {}))
		self.token = TokenGenerator(**kwargs.pop('token', {}))

		self.database = Database(loop=self.loop, config=kwargs.pop('database', {}))
		self.httpclient = HTTPClient(loop=self.loop)

		self.router = Router(loop=self.loop)
		self.router.setup_session(kwargs.pop('session_token', {}))

		self.config = kwargs or {}

		self.tools = Tools(self)
	
	async def initialize(self):
		await self.database.run()
		base = self.config.get('base', '')
		for package in dir(endpoints):
			if not package.startswith('e_'):
				continue
			endpoint = getattr(endpoints, package)
			rest_endpoint = endpoint.RestEndpoint(self)
			if rest_endpoint.path:
				self.router.add(base + rest_endpoint.path, rest_endpoint)
	
	def run(self):
		self.router.on_shutdown(self.kill)
		self.router.run(self.host, self.port, cloudflare=self.cloudflare)
	
	async def kill(self, app):
		await self.database.close()
		await self.httpclient.close()