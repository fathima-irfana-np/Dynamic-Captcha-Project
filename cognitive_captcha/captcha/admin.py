from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
import json
from django.contrib import admin
from .models import CaptchaAttempt, CaptchaChallenge

@admin.register(CaptchaAttempt)
class CaptchaAttemptAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'attempts', 'last_attempt', 'is_blocked')
    list_filter = ('is_blocked',)
    search_fields = ('identifier',)

@admin.register(CaptchaChallenge)
class CaptchaChallengeAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'scene', 'difficulty', 'created_at')
    list_filter = ('difficulty', 'scene')
    search_fields = ('question', 'identifier')
    readonly_fields = ('created_at',)
# from .models import CaptchaChallenge

# class CaptchaChallengeForm(forms.ModelForm):
#     class Meta:
#         model = CaptchaChallenge
#         fields = '__all__'

#     def clean_animation_data(self):
#         data = self.cleaned_data['animation_data']
#         try:
#             json.loads(data)  # Basic JSON check
#             return data
#         except json.JSONDecodeError:
#             raise ValidationError("Invalid JSON format")

# @admin.register(CaptchaChallenge)
# class CaptchaChallengeAdmin(admin.ModelAdmin):
#     form = CaptchaChallengeForm
#     list_display = ('id', 'question_preview', 'created_at')
    
#     def question_preview(self, obj):
#         return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
#     question_preview.short_description = "Question"
