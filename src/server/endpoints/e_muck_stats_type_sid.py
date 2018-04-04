import datetime

from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import IdTypes, PerspectiveAttributes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck/stats/{idtype}/{sid}'

		self.types = {'id': 'snowflake'}

		self.id_types = {
			'GUILDS': 'guild_id',
			'CHANNELS': 'channel_id',
			'USERS': 'user_id'
		}
	
	async def get(self, request, idtype, sid):
		idtype = IdTypes.get(idtype.upper())
		if not idtype:
			raise InvalidUsage(404)
		
		idt = self.id_types.get(idtype.name)

		#implement using timestamp

		scores = {}
		
		where = [
			'`timestamp` = 0',
			'`{}` = %s'.format(idt)
		]
		values = [sid]

		if idt == 'user_id':
			guild_id = request.query.get('guild_id', None)
			channel_id = request.query.get('channel_id', None)

			if guild_id and channel_id:
				raise InvalidUsage(400, 'Pick between guild_id and channel_id, not both')

			if guild_id:
				where.append('`guild_id` = %s')
				values.append(guild_id)

			if channel_id:
				where.append('`channel_id` = %s')
				values.append(channel_id)

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute(
					' '.join([
						'SELECT',
						', '.join([
							'`count`',
							', '.join(['`{}`'.format(attribute.value) for attribute in PerspectiveAttributes])
						]),
						'FROM `muck_averages` WHERE',
						' AND '.join(where)
					]),
					values
				)
				scores.update(await cur.fetchone())
		finally:
			self.server.database.release(connection)
		
		return Response(200, scores)
