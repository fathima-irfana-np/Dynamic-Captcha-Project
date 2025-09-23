from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
import json

from .models import CaptchaAttempt   


@admin.register(CaptchaAttempt)
class CaptchaAttemptAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'attempts', 'last_attempt', 'is_blocked')
    list_filter = ('is_blocked',)
    search_fields = ('identifier',)
