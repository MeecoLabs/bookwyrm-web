""" database schema for oauth """

from django.db import models
from django.utils import timezone

from bookwyrm.models import User

class OAuthAuthorizationCode(models.Model):
	""" oauth authorization code """

	code = models.CharField(max_length=255)
	client_id = models.TextField()
	scopes = models.TextField()
	redirect_uri = models.TextField()
	state = models.TextField(null=True)
	code_challenge = models.TextField(null=True)
	code_challenge_method = models.TextField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	created_date = models.DateTimeField(default=timezone.now)

class OAuthBearerToken(models.Model):
	""" oauth access or refresh token """

	token = models.CharField(max_length=255)
	client_id = models.TextField()
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	scope = models.TextField()
	created_date = models.DateTimeField(default=timezone.now)
	expiration_date = models.DateTimeField()
	refresh_token = models.CharField(max_length=255, null=True)
