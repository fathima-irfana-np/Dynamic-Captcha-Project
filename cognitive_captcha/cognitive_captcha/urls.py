from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('captcha.urls')),
    path('animations/<path:path>', serve, {'document_root': os.path.join(settings.BASE_DIR, 'animations')}),
]
# THIS PART IS CRITICAL FOR MEDIA FILES
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)