""" currently reading """
from django.http import JsonResponse

from bookwyrm.oauth import provider
from bookwyrm.views.feed import get_suggested_books
from bookwyrm.settings import DOMAIN, MEDIA_URL

def map_readthrough(readthrough):
	return {
		'id': readthrough.id,
		'progress': readthrough.progress or 0,
		'mode': readthrough.progress_mode,
	} if readthrough else None

def map_author(author):
	return {
		'id': author.id,
		'name': author.name,
	}

def map_book(book):
	return {
		'id': book.id,
		'title': book.title,
		'authors': list(map(map_author, book.authors.all())),
		'cover': f"https://{DOMAIN}{MEDIA_URL}{book.cover}" if book.cover else None,
		'latest_readthrough': map_readthrough(book.latest_readthrough),
	}

@provider.protected_resource_view(scopes=['user', 'shelf'])#, is_optional=False)
def currently_reading(request):
	suggested_books = get_suggested_books(request.user)
	reading_shelf = next(filter(lambda shelf: shelf['identifier'] == 'reading', suggested_books))
	books = list(map(map_book, reading_shelf['books']))
	return JsonResponse(books, safe=False)
