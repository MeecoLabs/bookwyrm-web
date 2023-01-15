""" currently reading """
from django.http import JsonResponse

from bookwyrm.oauth import provider
from bookwyrm.views.feed import get_suggested_books
from bookwyrm.settings import DOMAIN, MEDIA_URL

def copy_attrs(origin, attrs):
	result = {}
	for attr in attrs:
		result[attr] = getattr(origin, attr)
	return result

def map_readthrough(readthrough):
	return copy_attrs(readthrough, ['id', 'progress', 'progress_mode']) if readthrough else None

def map_author(author):
	return copy_attrs(author, ['id', 'name'])

def map_book(book):
	result = copy_attrs(book, ['id', 'title'])
	result['authors'] = list(map(map_author, book.authors.all()))
	result['cover'] = f"https://{DOMAIN}{MEDIA_URL}{book.cover}" if book.cover else None
	result['latest_readthrough'] = map_readthrough(book.latest_readthrough)
	return result

@provider.protected_resource_view(scopes=['user'])
def currently_reading(request):
	suggested_books = get_suggested_books(request.user)
	reading_shelf = next(filter(lambda shelf: shelf['identifier'] == 'reading', suggested_books))
	data = list(map(map_book, reading_shelf['books']))
	return JsonResponse(data, safe=False)
