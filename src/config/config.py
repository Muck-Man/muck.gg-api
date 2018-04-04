cfg = {
	'host': '127.0.0.1',
	'port': 4001,
	'base': '/api',
	'cloudflare': True,
	'oauth2': {
		'token_uri': 'https://muck.gg/auth/callback',
		'discord': {
			'id': '',
			'secret': '',
			'redirect_uri': 'https://muck.gg/api/bot/discord/oauth2/callback',
			'invite': 'https://discord.gg/kcPjgg3'
		},
		'github': {
			'url': 'https://github.com/Muck-Man'
		}
	},
	'googleapi': {
		'perspective': {
			'token': ''
		}
	},
	'database': {
		'host': '127.0.0.1',
		'user': '',
		'password': '',
		'db': 'muck',
		'charset': 'utf8mb4'
	}
}