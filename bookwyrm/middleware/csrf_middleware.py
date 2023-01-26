from django.middleware.csrf import CsrfViewMiddleware
from bookwyrm.views.helpers import is_api_request

class RestCsrfViewMiddleware(CsrfViewMiddleware):
	def process_view(self, request, callback, callback_args, callback_kwargs):
		if is_api_request(request) and request.user.is_authenticated:
			return None
		super().process_view(request, callback, callback_args, callback_kwargs)

