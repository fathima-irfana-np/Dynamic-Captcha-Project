from django.contrib import admin
from .models import CaptchaAttempt, Animation

@admin.register(CaptchaAttempt)
class CaptchaAttemptAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'attempts', 'last_attempt', 'is_blocked')
    list_filter = ('is_blocked',)
    search_fields = ('identifier',)
    readonly_fields = ('last_attempt',)

@admin.register(Animation)
class AnimationAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    list_per_page = 25
    readonly_fields = ('created_at',)