"""
Views for college recommendations.
"""

import sys
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings

# Add project root to path for AI engine imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from .models import College, Branch, CollegeBranchCutoff, SavedRecommendation, RecommendationHistory
from accounts.models import StudentPreference


def home_view(request):
    """Landing page."""
    context = {
        'total_colleges': College.objects.count(),
        'total_branches': Branch.objects.count(),
        'top_colleges': College.objects.filter(ranking__lte=10)[:6],
    }
    return render(request, 'home.html', context)


@login_required
def recommendations_view(request):
    """Generate and display recommendations."""
    user = request.user
    
    if not user.marks_entered:
        messages.warning(request, 'Please enter your marks first to get recommendations.')
        return redirect('marks_entry')
    
    # Get user data for AI engine
    student_data = user.to_dict()
    
    # Try to use AI engine
    try:
        from ai_engine.recommendation_engine import RecommendationEngine
        
        engine = RecommendationEngine(data_path=str(settings.PROCESSED_DATA_PATH))
        
        # Get preferences if available
        preferences = {}
        try:
            pref = user.preferences
            preferences = {
                'college_type': pref.college_type if pref.college_type != 'Any' else None,
                'min_placement_rate': pref.min_placement_rate,
            }
        except StudentPreference.DoesNotExist:
            pass
        
        result = engine.generate_recommendations(student_data, preferences)
        
        # Check if user's preferred district had results
        if user.preference_district and user.preference_district != 'Any':
            district_matches = [r for r in result.recommendations 
                              if r.district.lower() == user.preference_district.lower()]
            if not district_matches and result.recommendations:
                messages.info(request, 
                    f'No colleges found in {user.preference_district} matching your criteria. '
                    f'Showing best matches from other districts.')
        
        # Save to history
        if result.recommendations:
            RecommendationHistory.objects.create(
                user=user,
                cutoff_score=user.cutoff_score,
                category=user.category,
                preferred_branches=','.join(user.get_preferred_branches()),
                preferred_districts=user.preference_district,
                total_recommendations=result.total_recommendations,
                top_college=result.recommendations[0].college_name if result.recommendations else ''
            )
        
        context = {
            'result': result,
            'recommendations': result.recommendations,
            'insights': result.insights,
            'scholarship_summary': result.scholarship_summary,
            'district_recommendations': result.district_recommendations,
            'user': user,
        }
        
    except Exception as e:
        # Fallback to database query if AI engine fails
        messages.warning(request, f'Using basic recommendations. AI engine: {str(e)}')
        
        # Build query with filters
        cutoffs = CollegeBranchCutoff.objects.filter(
            cutoff_2023__lte=user.cutoff_score,
            category=user.category
        ).select_related('college', 'branch')
        
        # Filter by preferred district if selected (not "Any")
        if user.preference_district and user.preference_district != 'Any':
            cutoffs = cutoffs.filter(college__district__icontains=user.preference_district)
        
        cutoffs = cutoffs.order_by('-cutoff_2023')[:20]
        
        # If no results with district filter, show all with a message
        if not cutoffs.exists() and user.preference_district and user.preference_district != 'Any':
            messages.info(request, f'No colleges found in {user.preference_district} matching your cutoff. Showing all available options.')
            cutoffs = CollegeBranchCutoff.objects.filter(
                cutoff_2023__lte=user.cutoff_score,
                category=user.category
            ).select_related('college', 'branch').order_by('-cutoff_2023')[:20]
        
        context = {
            'fallback_mode': True,
            'cutoffs': cutoffs,
            'recommendations': [],  # Empty list for template compatibility
            'user': user,
            'filtered_district': user.preference_district if user.preference_district != 'Any' else None,
        }
    
    return render(request, 'recommendations/recommendations.html', context)


@login_required
def college_detail_view(request, college_id):
    """College detail page."""
    college = get_object_or_404(College, college_id=college_id)
    cutoffs = college.cutoffs.all().order_by('branch__branch_code', 'category')
    
    # Group cutoffs by branch
    branches_data = {}
    for cutoff in cutoffs:
        branch_code = cutoff.branch.branch_code
        if branch_code not in branches_data:
            branches_data[branch_code] = {
                'name': cutoff.branch.branch_name,
                'cutoffs': []
            }
        branches_data[branch_code]['cutoffs'].append(cutoff)
    
    # Check if user can apply
    user = request.user
    can_apply = False
    eligible_branches = []
    
    if user.is_authenticated and user.cutoff_score:
        for cutoff in cutoffs:
            if cutoff.cutoff_2023 <= user.cutoff_score and cutoff.category == user.category:
                can_apply = True
                eligible_branches.append(cutoff.branch.branch_code)
    
    context = {
        'college': college,
        'branches_data': branches_data,
        'can_apply': can_apply,
        'eligible_branches': eligible_branches,
    }
    
    return render(request, 'recommendations/college_detail.html', context)


@login_required
def save_recommendation(request, college_id, branch_code):
    """Save a recommendation to favorites."""
    if request.method == 'POST':
        user = request.user
        college = get_object_or_404(College, college_id=college_id)
        branch = get_object_or_404(Branch, branch_code=branch_code)
        
        cutoff = CollegeBranchCutoff.objects.filter(
            college=college,
            branch=branch,
            category=user.category
        ).first()
        
        if cutoff:
            saved, created = SavedRecommendation.objects.get_or_create(
                user=user,
                college=college,
                branch=branch,
                category=user.category,
                defaults={
                    'rank': 0,
                    'total_score': 0,
                    'cutoff': cutoff.cutoff_2023,
                    'margin': user.cutoff_score - cutoff.cutoff_2023,
                    'admission_probability': 'To be calculated',
                }
            )
            
            if created:
                messages.success(request, f'Saved {college.college_name} - {branch.branch_name}')
            else:
                messages.info(request, 'Already saved!')
        
        return redirect('recommendations')
    
    return redirect('recommendations')


@login_required
def saved_recommendations_view(request):
    """View saved recommendations."""
    saved = SavedRecommendation.objects.filter(user=request.user).select_related('college', 'branch')
    
    context = {
        'saved_recommendations': saved,
        'favorites': saved.filter(is_favorite=True),
    }
    
    return render(request, 'recommendations/saved.html', context)


@login_required
def toggle_favorite(request, pk):
    """Toggle favorite status."""
    saved = get_object_or_404(SavedRecommendation, pk=pk, user=request.user)
    saved.is_favorite = not saved.is_favorite
    saved.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'is_favorite': saved.is_favorite})
    
    return redirect('saved_recommendations')


@login_required
def delete_saved(request, pk):
    """Delete saved recommendation."""
    saved = get_object_or_404(SavedRecommendation, pk=pk, user=request.user)
    saved.delete()
    messages.success(request, 'Removed from saved list.')
    return redirect('saved_recommendations')


def college_list_view(request):
    """List all colleges with filters."""
    colleges = College.objects.all()
    
    # Apply filters
    college_type = request.GET.get('type')
    district = request.GET.get('district')
    search = request.GET.get('search')
    
    if college_type:
        colleges = colleges.filter(college_type=college_type)
    if district:
        colleges = colleges.filter(district__icontains=district)
    if search:
        colleges = colleges.filter(college_name__icontains=search)
    
    # Get filter options
    types = College.objects.values_list('college_type', flat=True).distinct()
    districts = College.objects.values_list('district', flat=True).distinct()
    
    context = {
        'colleges': colleges,
        'types': types,
        'districts': districts,
        'current_type': college_type,
        'current_district': district,
        'search_query': search,
    }
    
    return render(request, 'recommendations/college_list.html', context)


@login_required
def compare_colleges(request):
    """Compare multiple colleges."""
    college_ids = request.GET.getlist('colleges')
    
    if len(college_ids) < 2:
        messages.warning(request, 'Please select at least 2 colleges to compare.')
        return redirect('college_list')
    
    colleges = College.objects.filter(college_id__in=college_ids)
    
    # Get cutoffs for user's category
    user = request.user
    comparison_data = []
    
    for college in colleges:
        cutoffs = college.cutoffs.filter(category=user.category) if user.category else college.cutoffs.all()
        comparison_data.append({
            'college': college,
            'cutoffs': cutoffs[:5],  # Top 5 branches
        })
    
    context = {
        'comparison_data': comparison_data,
        'user': user,
    }
    
    return render(request, 'recommendations/compare.html', context)


@login_required
def recommendation_history_view(request):
    """View recommendation history."""
    history = RecommendationHistory.objects.filter(user=request.user)[:20]
    
    return render(request, 'recommendations/history.html', {'history': history})









