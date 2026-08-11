from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('accounts/social/', include('allauth.urls')),  # Facebook login (django-allauth)
    path('projects/', include('projects.urls', namespace='projects')),
    path('donations/', include('donations.urls', namespace='donations')),
    path('interactions/', include('interactions.urls', namespace='interactions')),
    path('', include('core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
