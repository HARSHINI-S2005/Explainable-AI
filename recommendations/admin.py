"""
Admin configuration for recommendations app.
"""

from django.contrib import admin
from .models import College, Branch, CollegeBranchCutoff, SavedRecommendation, RecommendationHistory


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ['college_id', 'college_name', 'college_type', 'district', 'ranking', 'placement_rate']
    list_filter = ['college_type', 'district', 'accreditation']
    search_fields = ['college_name', 'college_id', 'district']
    ordering = ['ranking']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['branch_code', 'branch_name', 'popularity_score']
    search_fields = ['branch_code', 'branch_name']


@admin.register(CollegeBranchCutoff)
class CutoffAdmin(admin.ModelAdmin):
    list_display = ['college', 'branch', 'category', 'cutoff_2023', 'seats_available']
    list_filter = ['category', 'college__college_type', 'branch']
    search_fields = ['college__college_name', 'branch__branch_code']
    ordering = ['-cutoff_2023']


@admin.register(SavedRecommendation)
class SavedRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'college', 'branch', 'rank', 'is_favorite', 'created_at']
    list_filter = ['is_favorite', 'created_at']
    search_fields = ['user__username', 'college__college_name']


@admin.register(RecommendationHistory)
class RecommendationHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'cutoff_score', 'category', 'total_recommendations', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['user__username']










