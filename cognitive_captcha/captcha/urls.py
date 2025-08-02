from django.urls import path
from . import views

urlpatterns = [
    path('', views.captcha_page),
    path('get/', views.get_captcha),
    path('submit/', views.submit_captcha_answer),
    path('protected/', views.protected_page),
    # path('api/get-captcha/', views.get_captcha),
    # path('api/verify-captcha/', views.verify_captcha),
     path('protected-page/', views.protected_page, name='protected-page'),

  
]

