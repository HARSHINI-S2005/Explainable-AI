"""
Admin configuration for scholarships app.
"""

from django.contrib import admin
from .models import Scholarship, ScholarshipApplication


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ['scholarship_id', 'scholarship_name', 'provider', 'amount_per_year', 'category_eligible']
    list_filter = ['provider', 'amount_category', 'gender']
    search_fields = ['scholarship_name', 'provider']
    ordering = ['-amount_per_year']


@admin.register(ScholarshipApplication)
class ScholarshipApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'scholarship', 'status', 'match_score', 'created_at']
    list_filter = ['status', 'eligibility_status']
    search_fields = ['user__username', 'scholarship__scholarship_name']










