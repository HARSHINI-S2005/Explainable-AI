"""
URL patterns for scholarships app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.scholarship_list_view, name='scholarship_list'),
    path('eligibility/', views.scholarship_eligibility_view, name='scholarship_eligibility'),
    path('<str:scholarship_id>/', views.scholarship_detail_view, name='scholarship_detail'),
    path('<str:scholarship_id>/apply/', views.apply_scholarship, name='apply_scholarship'),
    path('my/', views.my_scholarships_view, name='my_scholarships'),
]










