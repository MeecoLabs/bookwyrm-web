""" responds to OAuth requests """

from django.views import View
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from bookwyrm.oauth import client_information_discovery, extract_params, server, OAUTH_SCOPES
from oauthlib.oauth2 import FatalClientError, OAuth2Error

def response_from_return(headers, body, status):
	response = HttpResponse(content=body, status=status)
	for k, v in headers.items():
		response[k] = v
	return response

def response_from_error(e):
	return HttpResponseBadRequest('Evil client is unable to send a proper request. Error is: ' + e.description)

class Authorize(View):
	def __init__(self):
		self._authorization_endpoint = server

	def get(self, request):
		try:
			uri, http_method, body, headers = extract_params(request)
			scopes, credentials = self._authorization_endpoint.validate_authorization_request(uri, http_method, body, headers)
			del credentials["request"]
			request.session["oauth2_scopes"] = scopes
			request.session["oauth2_credentials"] = credentials
			if not request.user.is_authenticated:
				return redirect("login")

			data = {
				"client": client_information_discovery(credentials["client_id"]),
				"scopes": (OAUTH_SCOPES[scope] for scope in scopes),
			}
			return TemplateResponse(request, "oauth/authorize.html", data)
		except FatalClientError as e:
			del request.session["oauth2_scopes"]
			del request.session["oauth2_credentials"]
			return response_from_error(e)
		except OAuth2Error as e:
			del request.session["oauth2_scopes"]
			del request.session["oauth2_credentials"]
			return HttpResponseRedirect(e.in_uri(e.redirect_uri))

	def post(self, request):
		if request.POST.get("cancel"):
			credentials = request.session.get('oauth2_credentials', {})
			headers = {
				"Location": credentials["redirect_uri"] + "?state=" + credentials["state"] + "&error=user_cancelled"
			}
			del request.session["oauth2_scopes"]
			del request.session["oauth2_credentials"]
			return response_from_return(headers, None, 303)

		uri, http_method, body, headers = extract_params(request)

		scopes = request.session.get("oauth2_scopes", [])

		credentials = {'user': request.user}
		credentials.update(request.session.get('oauth2_credentials', {}))

		try:
			headers, body, status = self._authorization_endpoint.create_authorization_response(uri, http_method, body, headers, scopes, credentials)
			del request.session["oauth2_scopes"]
			del request.session["oauth2_credentials"]
			return response_from_return(headers, body, status)

		except FatalClientError as e:
			del request.session["oauth2_scopes"]
			del request.session["oauth2_credentials"]
			return response_from_error(e)

class Token(View):
	def __init__(self):
		self._token_endpoint = server

	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
			return super().dispatch(*args, **kwargs)

	def post(self, request):
		uri, http_method, body, headers = extract_params(request)

		credentials = { }

		headers, body, status = self._token_endpoint.create_token_response(uri, http_method, body, headers, credentials)

		return response_from_return(headers, body, status)
