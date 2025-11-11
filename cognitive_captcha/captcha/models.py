from django.db import models
from django.utils import timezone

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

class Animation(models.Model):
    title = models.CharField(max_length=200)
    video_file = models.FileField(upload_to='animations/')
    description = models.TextField(
    help_text="Describe the scene in detail as you would to a blind person"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title