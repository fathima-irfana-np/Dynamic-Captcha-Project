from django.db import models
from django.utils import timezone
import random

class CaptchaAttempt(models.Model):
    identifier = models.CharField(max_length=255)
    attempts = models.PositiveIntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)
    is_blocked = models.BooleanField(default=False)
    blocked_until = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['identifier']),
            models.Index(fields=['is_blocked']),
        ]
    
    @classmethod
    def get_or_create_for_identifier(cls, identifier):
        return cls.objects.get_or_create(
            identifier=identifier,
            defaults={'attempts': 0}
        )

class CaptchaChallenge(models.Model):
    identifier = models.CharField(max_length=255)
    scene = models.CharField(max_length=50)
    question = models.CharField(max_length=255)
    options = models.JSONField()
    correct_answer = models.CharField(max_length=50)
    animation_data = models.JSONField()
    difficulty = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']