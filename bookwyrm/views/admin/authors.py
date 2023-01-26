""" manage authors """
import string

from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.template.response import TemplateResponse
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.db.models import Q

from bookwyrm import models
from bookwyrm.settings import PAGE_LENGTH

alphabet = string.ascii_uppercase + "#"


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("bookwyrm.moderate_book_data", raise_exception=True),
    name="dispatch",
)
class ManageAuthors(View):
    def get(self, request):
        """list all authors"""
        start = request.GET.get("start", "A")
        authors = models.Author.objects
        if start:
            authors = authors.filter(name__istartswith=start)
        else:
            exclude = Q()
            for char in string.ascii_uppercase:
                exclude = exclude | Q(name__istartswith=char)

            authors = authors.exclude(exclude)

        authors = authors.order_by("name")

        data = {
            "alphabet": alphabet,
            "authors": Paginator(authors, PAGE_LENGTH).get_page(
                request.GET.get("page")
            ),
        }
        return TemplateResponse(request, "settings/authors/list.html", data)


compare_authors_fields = [
    "name",
    "aliases",
    "bio",
    "wikipedia_link",
    "website",
    "born",
    "died",
    "openlibrary_key",
    "inventaire_id",
    "librarything_key",
    "goodreads_key",
    "isfdb",
    "isni",
]

author_field_support_join = ["aliases"]


class MergeAuthors(View):
    def get(self, request):
        """confirm merging authors"""
        author_ids = list(map(lambda id: int(id), request.GET.getlist("authors")))
        authors = models.Author.objects.filter(id__in=author_ids)

        author_matrix = {}
        for field in compare_authors_fields:
            author_matrix[field] = {
                "supports_join": field in author_field_support_join,
                "authors": [
                    {
                        "id": str(author.id),
                        "value": getattr(author, field),
                        "selected": False,
                    }
                    for author in authors
                ],
            }

        for field in author_matrix:
            authors = author_matrix[field]["authors"]
            selected = False
            for data in authors:
                if data["value"] is not None:
                    data["selected"] = True
                    selected = True
                    break
            if not selected:
                authors[0]["selected"] = True

        data = {
            "author_ids": author_ids,
            "author_matrix": author_matrix,
        }
        return TemplateResponse(request, "settings/authors/merge.html", data)

    def post(self, request):
        """merge authors"""
        author_ids = request.POST.get("author_ids").split(",")
        author_ids = list(map(lambda id: int(id), author_ids))
        authors_list = models.Author.objects.filter(id__in=author_ids).order_by(
            "created_date"
        )
        authors = dict(map(lambda author: (author.id, author), authors_list))

        fields = {}
        for field in compare_authors_fields:
            chosen_author = request.POST.get(f"field-{field}")
            if chosen_author:
                chosen_author = int(chosen_author)
            else:
                chosen_author = None
            if chosen_author is None:
                fields[field] = []
                for id in author_ids:
                    fields[field] = fields[field] + getattr(authors[id], field)
            else:
                fields[field] = getattr(authors[chosen_author], field)

        # update oldest author with selected fields
        oldest_author = authors_list.first()
        for field in fields:
            setattr(oldest_author, field, fields[field])
        oldest_author.save()

        other_authors = authors_list.exclude(id=oldest_author.id)

        # move other authors’ books to oldest author
        books = models.Book.objects.filter(authors__in=other_authors).distinct()
        for book in books:
            book.authors.add(oldest_author)
            book.authors.remove(*other_authors)

        # redirect old authors to oldest
        for author in other_authors:
            merged_author = models.MergedAuthor(id=author.id, merged_with=oldest_author)
            merged_author.save()

        other_authors.delete()

        return redirect("settings-manage-authors")
