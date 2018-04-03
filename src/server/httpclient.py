import aiohttp
import asyncio
import base64
import json
import sys

from urllib.parse import urlencode
from urllib.parse import quote as _uriquote

def urlquery(url, **parameters):
	return '{}:{}'.format(url, urlencode(parameters))

class Route:
	def __init__(self, method, url, **parameters):
		self.method = method
		if parameters:
			self.url = url.format(**{k: _uriquote(v) if isinstance(v, str) else v for k, v in parameters.items()})
		else:
			self.url = url

class HTTPClient:
	def __init__(self, **kwargs):
		self.loop = kwargs.pop('loop', asyncio.get_event_loop())

		self._session = aiohttp.ClientSession(loop=self.loop)

		user_agent = 'NotSoPhone Website (https://notsophone.com {}) Python/{} aiohttp/{}'
		self.user_agent = user_agent.format('0.0.1', sys.version_info, aiohttp.__version__)
	
	def recreate(self):
		if self._session.closed:
			self._session = aiohttp.ClientSession(loop=self.loop)
	
	async def close(self):
		if not self._session.closed:
			await self._session.close()
	
	async def request(self, route, *args, **kwargs):
		method = route.method
		url = route.url

		headers = kwargs.pop('headers', {})
		headers.update({'User-Agent': self.user_agent})

		if 'json' in kwargs:
			headers['content-type'] = 'application/json'
			kwargs['data'] = json.dumps(kwargs.pop('json'))
		
		kwargs['headers'] = headers

		response = await self._session.request(method, url, **kwargs)
		response = {
			'status': response.status,
			'json': (response.headers['content-type'].lower().startswith('application/json')),
			'data': await response.text(encoding='utf-8')
		}
		if response['json'] and response['data']:
			response['data'] = json.loads(response['data'])
		
		return response
	
	def discord_post_oauth2_token(self, client_id, client_secret, grant_type, redirect_uri, code=None, refresh_token=None):
		data = {
			'client_id': client_id,
			'client_secret': client_secret,
			'grant_type': grant_type,
			'redirect_uri': redirect_uri
		}
		if code:
			data['code'] = code
		if refresh_token:
			data['refresh_token'] = refresh_token
		return self.request(Route('post', 'https://discordapp.com/api/v6/oauth2/token'), data=data)
	
	def discord_get_users_me(self, token):
		return self.request(Route('get', 'https://discordapp.com/api/v6/users/@me'), headers={'Authorization': token})
	
	def googleapi_perspective(self, token, content, attributes, do_not_store):
		data = {
			'comment': {
				'text': content
			},
			'languages': ['en'],
			'requestedAttributes': attributes,
			'doNotStore': do_not_store
		}

		return self.request(Route('post', 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'), params={'key': token}, json=data)