import time

from server.rest.invalidusage import InvalidUsage

class Tools:
	def __init__(self, server, **kwargs):
		self.server = server

		self.loop = self.server.loop

		self.database = self.server.database
		self.httpclient = self.server.httpclient

		self.snowflake = self.server.snowflake
		self.token = self.server.token