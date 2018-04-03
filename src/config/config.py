cfg = {
	'host': '127.0.0.1',
	'port': 4001,
	'base': '/api',
	'cloudflare': True,
	'oauth2': {
		'token_uri': 'https://muck.gg/auth/callback',
		'discord': {
			'id': '409288585766764544',
			'secret': '',
			'redirect_uri': 'https://muck.gg/api/bot/discord/oauth2/callback'
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
		'db': '',
		'charset': 'utf8mb4'
	}
}