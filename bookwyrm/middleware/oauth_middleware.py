""" oauth authentication """
from bookwyrm.oauth import extract_params, server

class OAuthAuthenticationMiddleware:
	"""authenticate users based on their oauth bearer token"""
	
	def __init__(self, get_response):
		self.get_response = get_response
		self._resource_endpoint = server
	
	def __call__(self, request):
		try:
			if not request.path.startswith('/oauth') and not request.user.is_authenticated:
				uri, http_method, body, headers = extract_params(request)

				valid, r = self._resource_endpoint.verify_request(uri, http_method, body, headers, None)
				if valid:
					request.user = r.user
					#request.client = r.client
		except:
			pass
		
		return self.get_response(request)
