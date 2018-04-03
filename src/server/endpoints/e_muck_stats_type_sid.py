from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck/stats/{idtype}/{sid}'

		self.types = {'id': 'snowflake'}

		self.attributes = [
			'attack_on_author',
			'attack_on_commenter',
			'incoherent',
			'inflammatory',
			'likely_to_reject',
			'obscene',
			'severe_toxicity',
			'spam',
			'toxicity',
			'unsubstantial'
		]

		self.idtypes = ['guilds', 'channels', 'users']
	
	async def get(self, request, idtype, sid):
		if idtype not in self.idtypes:
			raise InvalidUsage(404, 'Allowed ID Types: [{}]'.format(', '.join(self.idtypes)))

		scores = {
			'unique': None,
			'duplicates': None
		}
		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				await cur.execute(
					' '.join([
						'SELECT',
						'COUNT(*) AS "messages",',
						'{}'.format(', '.join(['AVG(`muck_cache`.`{a}`) AS "{a}"'.format(a=attribute) for attribute in self.attributes])),
						'FROM `muck_messages`',
						'WHERE `{}` = %s'
						'INNER JOIN `muck_cache` ON `muck_messages`.`hash` = `muck_cache`.`hash`'
					]),
					(sid,)
				)
				scores['duplicates'] = await cur.fetchone()

				await cur.execute(
					' '.join([
						'SELECT',
						'COUNT(*) AS "messages",',
						'{}'.format(', '.join(['AVG(`uniques`.`{a}`) AS "{a}"'.format(a=attribute) for attribute in self.attributes])),
						'FROM (SELECT',
						'{}'.format(', '.join(['`muck_cache`.`{a}` AS "{a}"'.format(a=attribute) for attribute in self.attributes])),
						'FROM `muck_messages` INNER JOIN `muck_cache` ON `muck_messages`.`hash` = `muck_cache`.`hash` GROUP BY `muck_messages`.`hash`) AS `uniques`'
					])
				)
				scores['unique'] = await cur.fetchone()
		finally:
			self.server.database.release(connection)
		
		return Response(200, scores)
