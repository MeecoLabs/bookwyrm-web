from django.http import HttpRequest, HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from urllib.parse import urljoin, urlencode
import requests
import mf2py
import functools

from oauthlib.oauth2 import RequestValidator, WebApplicationServer
from requests import RequestException
from bookwyrm.models import OAuthAuthorizationCode, OAuthBearerToken

OAUTH_SCOPES = {
	"user": "Read/write access to profile info."
}

class OAuthClient:
	def __init__(self, client_id, url, name, logo, redirect_uri):
		self.client_id = client_id
		self.url = url
		self.name = name
		self.logo = logo
		self.redirect_uri = redirect_uri

def authorize_next_param(request, default = None):
	credentials = request.session.get("oauth2_credentials", None)
	scopes = request.session.get("oauth2_scopes", None)
	if credentials is not None and scopes is not None:
		params = credentials | { "scope": " ".join(scopes) }
		return f"/oauth/authorize?{urlencode(params)}"
	else:
		return default

def client_information_discovery(client_id):
	try:
		response = requests.get(client_id)
		if response.status_code != 200:
			return None
		
		mf2_client = mf2py.parse(doc=response.text)
		app_item = next((item for item in mf2_client["items"] if (lambda item: item["type"] == "h-app")), None)
		plain_logo = app_item["properties"]["logo"][0]
		client = {
			"client_id": client_id,
			"url": client_id,
			"name": app_item["properties"]["name"][0],
			"summary": app_item["properties"]["summary"][0],
			"logo": plain_logo if plain_logo.startswith("https://") else urljoin(client_id, plain_logo),
			"redirect_uri": mf2_client["rels"]["redirect_uri"][0]
		}
		return client
	except RequestException:
		return None

class WyrmRequestValidator(RequestValidator):
	def validate_client_id(self, client_id, request):
		try:
			# TODO: ensure client id is a https url and does not resolve to localhost
			# TODO: ensure client id was not blocked in a local database
			client = client_information_discovery(client_id)
			return True if client is not None else False
		except:
			return False

	def validate_redirect_uri(self, client_id, redirect_uri, request):
		try:
			client = client_information_discovery(client_id)
			return True if redirect_uri == client["redirect_uri"] else False
		except:
			return False

	def validate_scopes(self, client_id, scopes, client, request):
		valid_scopes = OAUTH_SCOPES.keys()
		for scope in scopes:
			if scope not in valid_scopes:
				return False
		return True

	def is_pkce_required(self, client_id, request):
		return True
	
	def validate_response_type(self, client_id, response_type, client, request):
		return True if response_type == "code" else False

	def save_authorization_code(self, client_id, code, request):
		OAuthAuthorizationCode.objects.create(
			code = code["code"],
			state = code["state"],
			client_id = client_id,
			scopes = " ".join(request.scopes),
			redirect_uri = request.redirect_uri,
			code_challenge = request.code_challenge,
			code_challenge_method = request.code_challenge_method,
			user = request.user,
		)

	def authenticate_client(self, request):
		try:
			# TODO: ensure client id is a https url and does not resolve to localhost
			# TODO: ensure client id was not blocked in a local database
			client_dict = client_information_discovery(request.client_id)
			if client_dict is None:
				return False
			client = OAuthClient(
				client_dict["client_id"],
				client_dict["url"],
				client_dict["name"],
				client_dict["logo"],
				client_dict["redirect_uri"],
			)
			request.client = client
			return True
		except:
			return False

	def authenticate_client_id(self, client_id, request):
		return True

	def validate_code(self, client_id, code, client, request):
		auth_code = OAuthAuthorizationCode.objects.get(code=code)
		if auth_code is None or auth_code.client_id != client_id:
			return False

		request.user = auth_code.user
		request.scopes = auth_code.scopes.split(" ")
		request.code_challenge = auth_code.code_challenge
		request.code_challenge_method = auth_code.code_challenge_method
		return True

	def confirm_redirect_uri(self, client_id, code, redirect_uri, client, request):
		auth_code = OAuthAuthorizationCode.objects.get(code=code)
		return False if auth_code is None or auth_code.client_id != client_id or auth_code.redirect_uri != redirect_uri else True

	def validate_grant_type(self, client_id, grant_type, client, request):
		return True if grant_type == "authorization_code" or grant_type == "refresh_token" else False

	def get_code_challenge(self, code, request):
		auth_code = OAuthAuthorizationCode.objects.get(code=code)
		return None if auth_code is None else auth_code.code_challenge
	
	def get_code_challenge_method(self, code, request):
		auth_code = OAuthAuthorizationCode.objects.get(code=code)
		return None if auth_code is None else auth_code.code_challenge_method

	def save_bearer_token(self, token, request):
		# TODO: log history of clients used so a bad player can be found more easily
		OAuthBearerToken.objects.create(
			token = token["access_token"],
			client_id = request.client.client_id,
			user = request.user,
			scope = " ".join(request.scopes),
			expiration_date = timezone.now() + timedelta(seconds=token["expires_in"]),
			refresh_token = token["refresh_token"],
		)
		# Add username so the oauth client can access their own profile
		token["username"] = request.user.localname

	def invalidate_authorization_code(self, client_id, code, request):
		OAuthAuthorizationCode.objects.filter(code=code, client_id=client_id).delete()

	def validate_refresh_token(self, refresh_token, client, request):
		token = OAuthBearerToken.objects.get(refresh_token=refresh_token)
		if token is None or token.client_id != client.client_id:
			return False
		
		request.user = token.user
		return True

	def validate_bearer_token(self, token, scopes, request):
		token = OAuthBearerToken.objects.get(token=token)
		if token is None or token.expiration_date <= timezone.now():
			return False
		
		granted_scopes = token.scope.split(" ")
		if scopes is not None:
			for scope in scopes:
				if scope not in granted_scopes:
					return False

		request.user = token.user
		#request.client = token.client
		return True

	def get_original_scopes(self, refresh_token, request):
		token = OAuthBearerToken.objects.get(refresh_token=refresh_token)
		return None if token is None else token.scope.split(" ")


def extract_params(request: HttpRequest):
	return request.get_raw_uri(), request.method, request.body, request.headers

class OAuth2ProviderDecorator(object):
	def __init__(self, resource_endpoint):
		self._resource_endpoint = resource_endpoint

	def protected_resource_view(self, scopes):
		def decorator(f):
			@functools.wraps(f)
			def wrapper(request, *args, **kwargs):
				try:
					scopes_list = scopes(request)
				except TypeError:
					scopes_list = scopes

				uri, http_method, body, headers = extract_params(request)

				valid, r = self._resource_endpoint.verify_request(uri, http_method, body, headers, scopes_list)
				
				if valid:
					return f(request, *args, **kwargs)
				else:
					return HttpResponseForbidden()
			return wrapper
		return decorator

validator = WyrmRequestValidator()
server = WebApplicationServer(validator)
provider = OAuth2ProviderDecorator(server)
