"""
URL patterns for recommendations app.
"""

from django.urls import path
from . import views
from accounts.views import dashboard_view

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    path('colleges/', views.college_list_view, name='college_list'),
    path('colleges/compare/', views.compare_colleges, name='compare_colleges'),
    path('colleges/<str:college_id>/', views.college_detail_view, name='college_detail'),
    path('save/<str:college_id>/<str:branch_code>/', views.save_recommendation, name='save_recommendation'),
    path('saved/', views.saved_recommendations_view, name='saved_recommendations'),
    path('saved/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('saved/<int:pk>/delete/', views.delete_saved, name='delete_saved'),
    path('history/', views.recommendation_history_view, name='recommendation_history'),
]
