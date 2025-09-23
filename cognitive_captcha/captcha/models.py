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

