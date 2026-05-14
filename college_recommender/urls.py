"""
URL configuration for college_recommender project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Customize Admin Site
admin.site.site_header = "🎓 TN College Recommender Admin"
admin.site.site_title = "College Recommender Admin"
admin.site.index_title = "Welcome to TN Engineering College Recommendation System"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('recommendations.urls')),
    path('accounts/', include('accounts.urls')),
    path('scholarships/', include('scholarships.urls')),
    path('districts/', include('districts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)










