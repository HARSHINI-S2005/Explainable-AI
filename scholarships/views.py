"""
Views for scholarship management.
"""

import sys
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from .models import Scholarship, ScholarshipApplication


@login_required
def scholarship_list_view(request):
    """List all scholarships."""
    scholarships = Scholarship.objects.all()
    
    # Apply filters
    category = request.GET.get('category')
    amount = request.GET.get('amount')
    gender = request.GET.get('gender')
    
    if category and category != 'all':
        scholarships = scholarships.filter(category_eligible__icontains=category)
    if amount:
        scholarships = scholarships.filter(amount_category=amount)
    if gender and gender != 'All':
        scholarships = scholarships.filter(gender__in=[gender, 'All'])
    
    context = {
        'scholarships': scholarships,
        'current_category': category,
        'current_amount': amount,
        'current_gender': gender,
    }
    
    return render(request, 'scholarships/list.html', context)


@login_required
def scholarship_eligibility_view(request):
    """Check scholarship eligibility for the logged-in user."""
    user = request.user
    
    if not user.marks_entered:
        messages.warning(request, 'Please enter your marks first.')
        return redirect('marks_entry')
    
    # Get user data
    student_data = user.to_dict()
    
    try:
        from ai_engine.scholarship_engine import ScholarshipEngine
        import pandas as pd
        
        # Load scholarship data
        scholarship_df = pd.read_csv(settings.PROCESSED_DATA_PATH / 'scholarship_processed.csv')
        
        engine = ScholarshipEngine()
        report = engine.generate_scholarship_report(student_data, scholarship_df)
        
        context = {
            'report': report,
            'eligible_scholarships': report['eligible_scholarships'],
            'near_miss': report['near_miss_scholarships'],
            'financial_summary': report['financial_summary'],
            'recommendations': report['recommendations'],
            'user': user,
        }
        
    except Exception as e:
        messages.warning(request, f'Using basic eligibility check. {str(e)}')
        
        # Fallback to basic check
        scholarships = Scholarship.objects.all()
        eligible = []
        
        for s in scholarships:
            is_eligible = True
            
            # Check category
            if s.category_eligible.upper() != 'ALL':
                cats = [c.strip().upper() for c in s.category_eligible.split('/')]
                if user.category.upper() not in cats:
                    is_eligible = False
            
            # Check income
            if s.income_limit > 0 and user.annual_income and user.annual_income > s.income_limit:
                is_eligible = False
            
            # Check cutoff
            if s.min_cutoff > 0 and user.cutoff_score and user.cutoff_score < s.min_cutoff:
                is_eligible = False
            
            # Check gender
            if s.gender != 'All' and s.gender != user.gender:
                is_eligible = False
            
            if is_eligible:
                eligible.append(s)
        
        context = {
            'fallback_mode': True,
            'eligible_scholarships': eligible,
            'user': user,
        }
    
    return render(request, 'scholarships/eligibility.html', context)


@login_required
def scholarship_detail_view(request, scholarship_id):
    """Scholarship detail page."""
    scholarship = get_object_or_404(Scholarship, scholarship_id=scholarship_id)
    user = request.user
    
    # Check if user has applied/saved
    application = ScholarshipApplication.objects.filter(
        user=user, scholarship=scholarship
    ).first()
    
    # Quick eligibility check
    is_eligible = True
    eligibility_issues = []
    
    if scholarship.category_eligible.upper() != 'ALL':
        cats = [c.strip().upper() for c in scholarship.category_eligible.split('/')]
        if user.category.upper() not in cats:
            is_eligible = False
            eligibility_issues.append(f'Category {user.category} not eligible')
    
    if scholarship.income_limit > 0 and user.annual_income:
        if user.annual_income > scholarship.income_limit:
            is_eligible = False
            eligibility_issues.append(f'Income exceeds limit of ₹{scholarship.income_limit:,}')
    
    if scholarship.min_cutoff > 0 and user.cutoff_score:
        if user.cutoff_score < scholarship.min_cutoff:
            is_eligible = False
            eligibility_issues.append(f'Cutoff below minimum {scholarship.min_cutoff}')
    
    if scholarship.gender != 'All' and scholarship.gender != user.gender:
        is_eligible = False
        eligibility_issues.append(f'Only for {scholarship.gender} students')
    
    context = {
        'scholarship': scholarship,
        'application': application,
        'is_eligible': is_eligible,
        'eligibility_issues': eligibility_issues,
    }
    
    return render(request, 'scholarships/detail.html', context)


@login_required
def apply_scholarship(request, scholarship_id):
    """Mark interest or apply for scholarship."""
    scholarship = get_object_or_404(Scholarship, scholarship_id=scholarship_id)
    
    application, created = ScholarshipApplication.objects.get_or_create(
        user=request.user,
        scholarship=scholarship,
        defaults={'status': 'interested'}
    )
    
    if request.method == 'POST':
        status = request.POST.get('status', 'interested')
        notes = request.POST.get('notes', '')
        
        application.status = status
        application.notes = notes
        application.save()
        
        messages.success(request, f'Updated status for {scholarship.scholarship_name}')
    
    return redirect('scholarship_detail', scholarship_id=scholarship_id)


@login_required
def my_scholarships_view(request):
    """View user's scholarship applications."""
    applications = ScholarshipApplication.objects.filter(
        user=request.user
    ).select_related('scholarship')
    
    context = {
        'applications': applications,
        'interested': applications.filter(status='interested'),
        'applied': applications.filter(status='applied'),
        'pending': applications.filter(status='pending'),
    }
    
    return render(request, 'scholarships/my_scholarships.html', context)










