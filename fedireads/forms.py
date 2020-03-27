''' usin django model forms '''
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import ModelForm, PasswordInput, IntegerField
from django import forms

from fedireads import models


class LoginForm(ModelForm):
    class Meta:
        model = models.User
        fields = ['username', 'password']
        help_texts = {f: None for f in fields}
        widgets = {
            'password': PasswordInput(),
        }


class RegisterForm(ModelForm):
    class Meta:
        model = models.User
        fields = ['username', 'email', 'password']
        help_texts = {f: None for f in fields}
        widgets = {
            'password': PasswordInput(),
        }


class ReviewForm(ModelForm):
    class Meta:
        model = models.Review
        fields = ['name', 'rating', 'content']
        help_texts = {f: None for f in fields}
        content = IntegerField(validators=[
            MinValueValidator(0), MaxValueValidator(5)
        ])
        labels = {
            'name': 'Title',
            'rating': 'Rating (out of 5)',
            'content': 'Review',
        }


class CommentForm(ModelForm):
    class Meta:
        model = models.Comment
        fields = ['name', 'content']
        help_texts = {f: None for f in fields}
        labels = {
            'name': 'Title',
            'content': 'Comment',
        }


class ReplyForm(ModelForm):
    class Meta:
        model = models.Status
        fields = ['content']
        help_texts = {f: None for f in fields}
        labels = {'content': 'Comment'}


class EditUserForm(ModelForm):
    class Meta:
        model = models.User
        fields = ['avatar', 'name', 'summary', 'manually_approves_followers']
        help_texts = {f: None for f in fields}


class TagForm(ModelForm):
    class Meta:
        model = models.Tag
        fields = ['name']
        help_texts = {f: None for f in fields}
        labels = {'name': 'Add a tag'}


class ImportForm(forms.Form):
    csv_file = forms.FileField()
