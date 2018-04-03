from server.rest.endpoint import Endpoint
from server.rest.invalidusage import InvalidUsage
from server.rest.response import Response

from server.utils import IdTypes

class RestEndpoint(Endpoint):
	def __init__(self, server):
		super().__init__()
		self.server = server
		self.path = '/muck/stats'

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
	
	async def get(self, request):
		scores = {
			'guilds': {
				'unique': None,
				'duplicates': None
			},
			'channels': {
				'unique': None,
				'duplicates': None
			},
			'users': {
				'unique': None,
				'duplicates': None
			}
		}
		connection = await self.server.database.acquire()
		try:
			async with connection.cursor() as cur:
				for idt in scores.keys():
					id_type = IdTypes.get(idt.upper())

					await cur.execute(
						' '.join([
							'SELECT',
							'{}'.format(
								', '.join(
									['AVG(`{a}`) AS "{a}"'.format(a=attribute) for attribute in self.attributes] +
									['AVG(`unique_{a}`) AS "unique_{a}"'.format(a=attribute) for attribute in self.attributes] +
									['SUM(`count`) AS `count`', 'SUM(`unique_count`) AS `unique_count`']
								)
							),
							'FROM `muck_averages` WHERE `id_type` = %s'
						]),
						(id_type.value,)
					)
					score = await cur.fetchone()
					scores[idt]['duplicates'] = {k: float(score[k]) for k in self.attributes}
					scores[idt]['duplicates']['count'] = score['count']
					scores[idt]['unique'] = {k: float(score['unique_{}'.format(k)]) for k in self.attributes}
					scores[idt]['unique']['count'] = score['unique_count']
		finally:
			self.server.database.release(connection)
		
		return Response(200, scores)
