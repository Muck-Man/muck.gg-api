from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import PerspectiveAttributes, ThresholdIdTypes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck/thresholds/{itype}/{sid}'

		self.types = {'sid': 'snowflake'}

		self.allowed = ['guilds', 'channels']
	
	async def get(self, request, itype, sid):
		bot = await self.server.tools.authorize(
			request.headers.get('Authorization'),
			bot_permissions=['OWNER'],
			bots=True
		)

		if itype not in self.allowed:
			raise InvalidUsage(400, 'Invalid Id Type')
		
		itype = ThresholdIdTypes.get(itype.upper()[:-1])

		thresholds = {}
		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				if await cur.execute('SELECT * FROM `thresholds` WHERE `id` = %s AND `id_type` = %s', (sid, itype.value)):
					found = await cur.fetchone()
					thresholds.update({k.value: found[k.value] for k in PerspectiveAttributes})
				else:
					raise InvalidUsage(404, 'Thresholds not found for this id and id type')
		finally:
			self.server.database.release(connection)
		
		return Response(200, thresholds)

	async def put(self, request, itype, sid):
		bot = await self.server.tools.authorize(
			request.headers.get('Authorization'),
			bot_permissions=['OWNER'],
			bots=True
		)

		if itype not in self.allowed:
			raise InvalidUsage(400, 'Invalid Id Type')
		
		itype = ThresholdIdTypes.get(itype.upper()[:-1])

		data = self.validate(await request.json())

		thresholds = {}
		for key in data:
			threshold = PerspectiveAttributes.get(key.upper())
			if threshold:
				thresholds[threshold.value] = data[key]
			else:
				raise InvalidUsage(400, 'Invalid Attribute: {}'.format(key))

		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				ithresholds = thresholds.items()
				await cur.execute(
					' '.join([
						'INSERT INTO `thresholds`',
						'(`id`, `id_type`, {})'.format(', '.join(['`{}`'.format(k) for k, v in ithresholds])),
						'VALUES',
						'(%s, %s, {})'.format(', '.join(['%s' for a in range(len(thresholds))])),
						'ON DUPLICATE KEY UPDATE',
						', '.join(['`{k}` = ROUND(VALUES(`{k}`), 2)'.format(k=k) for k, v in ithresholds])
					]),
					[sid, itype.value] + [v for k, v in ithresholds]
				)
		finally:
			self.server.database.release(connection)
		
		return Response(204)