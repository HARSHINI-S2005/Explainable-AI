"""
Scholarship Eligibility Engine
Determines student eligibility for various scholarships
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScholarshipMatch:
    """Scholarship match result."""
    scholarship_id: str
    scholarship_name: str
    provider: str
    amount_per_year: float
    total_value: float
    duration_years: int
    match_score: float
    eligibility_status: str  # 'eligible', 'partial', 'ineligible'
    met_criteria: List[str]
    unmet_criteria: List[str]
    recommendation_priority: int


class ScholarshipEngine:
    """
    Evaluates student eligibility for scholarships.
    Provides match scores and recommendations.
    """
    
    def __init__(self):
        # Category mappings for scholarship eligibility
        self.category_groups = {
            'SC/ST': ['SC', 'ST', 'SCA'],
            'BC/MBC': ['BC', 'BCM', 'MBC', 'DNC'],
            'Minority': ['MUSLIM', 'CHRISTIAN', 'SIKH', 'BUDDHIST', 'JAIN', 'PARSI'],
            'All': ['OC', 'BC', 'BCM', 'MBC', 'DNC', 'SC', 'ST', 'SCA']
        }
        
        # Priority weights for ranking scholarships
        self.priority_weights = {
            'amount': 0.35,
            'duration': 0.15,
            'provider_reliability': 0.25,
            'accessibility': 0.25
        }
    
    def check_category_eligibility(self, student_category: str, 
                                    scholarship_categories: str) -> Tuple[bool, str]:
        """Check if student's category is eligible for scholarship."""
        student_cat = student_category.upper()
        
        # Parse scholarship categories
        if scholarship_categories.upper() == 'ALL':
            return True, "All categories eligible"
        
        eligible_cats = [c.strip().upper() for c in scholarship_categories.split('/')]
        
        # Direct match
        if student_cat in eligible_cats:
            return True, f"Category {student_cat} is eligible"
        
        # Check category groups
        for group_name, group_cats in self.category_groups.items():
            if group_name.upper() in eligible_cats:
                if student_cat in [c.upper() for c in group_cats]:
                    return True, f"Category {student_cat} eligible under {group_name}"
        
        return False, f"Category {student_cat} not in {eligible_cats}"
    
    def check_income_eligibility(self, annual_income: float, 
                                  income_limit: float) -> Tuple[bool, str]:
        """Check if student meets income criteria."""
        if income_limit <= 0:
            return True, "No income limit"
        
        if annual_income <= income_limit:
            margin = income_limit - annual_income
            return True, f"Income ₹{annual_income:,.0f} within limit ₹{income_limit:,.0f} (margin: ₹{margin:,.0f})"
        
        excess = annual_income - income_limit
        return False, f"Income ₹{annual_income:,.0f} exceeds limit ₹{income_limit:,.0f} by ₹{excess:,.0f}"
    
    def check_academic_eligibility(self, cutoff_score: float, percentage: float,
                                    min_cutoff: float, min_percentage: float) -> Tuple[bool, str]:
        """Check if student meets academic criteria."""
        reasons = []
        is_eligible = True
        
        if min_cutoff > 0:
            if cutoff_score >= min_cutoff:
                reasons.append(f"Cutoff {cutoff_score} meets minimum {min_cutoff}")
            else:
                is_eligible = False
                reasons.append(f"Cutoff {cutoff_score} below minimum {min_cutoff}")
        
        if min_percentage > 0:
            if percentage >= min_percentage:
                reasons.append(f"Percentage {percentage}% meets minimum {min_percentage}%")
            else:
                is_eligible = False
                reasons.append(f"Percentage {percentage}% below minimum {min_percentage}%")
        
        if not reasons:
            reasons.append("No academic criteria")
        
        return is_eligible, " | ".join(reasons)
    
    def check_gender_eligibility(self, student_gender: str, 
                                  scholarship_gender: str) -> Tuple[bool, str]:
        """Check if student meets gender criteria."""
        if scholarship_gender.lower() == 'all':
            return True, "Open to all genders"
        
        if student_gender.lower() == scholarship_gender.lower():
            return True, f"{scholarship_gender} students eligible"
        
        return False, f"Only {scholarship_gender} students eligible"
    
    def evaluate_scholarship(self, student_data: Dict, 
                              scholarship_data: Dict) -> ScholarshipMatch:
        """Evaluate a single scholarship for a student."""
        met_criteria = []
        unmet_criteria = []
        
        # Check category
        cat_eligible, cat_reason = self.check_category_eligibility(
            student_data.get('category', 'OC'),
            scholarship_data.get('category_eligible', 'ALL')
        )
        if cat_eligible:
            met_criteria.append(f"Category: {cat_reason}")
        else:
            unmet_criteria.append(f"Category: {cat_reason}")
        
        # Check income
        income_eligible, income_reason = self.check_income_eligibility(
            student_data.get('annual_income', 0),
            scholarship_data.get('income_limit', 0)
        )
        if income_eligible:
            met_criteria.append(f"Income: {income_reason}")
        else:
            unmet_criteria.append(f"Income: {income_reason}")
        
        # Check academics
        academic_eligible, academic_reason = self.check_academic_eligibility(
            student_data.get('cutoff_score', 0),
            student_data.get('total_percentage', 0),
            scholarship_data.get('min_cutoff', 0),
            scholarship_data.get('min_percentage', 0)
        )
        if academic_eligible:
            met_criteria.append(f"Academics: {academic_reason}")
        else:
            unmet_criteria.append(f"Academics: {academic_reason}")
        
        # Check gender
        gender_eligible, gender_reason = self.check_gender_eligibility(
            student_data.get('gender', 'Male'),
            scholarship_data.get('gender', 'All')
        )
        if gender_eligible:
            met_criteria.append(f"Gender: {gender_reason}")
        else:
            unmet_criteria.append(f"Gender: {gender_reason}")
        
        # Determine eligibility status
        total_criteria = len(met_criteria) + len(unmet_criteria)
        if not unmet_criteria:
            status = 'eligible'
            match_score = 100
        elif len(met_criteria) >= len(unmet_criteria):
            status = 'partial'
            match_score = (len(met_criteria) / total_criteria) * 100
        else:
            status = 'ineligible'
            match_score = (len(met_criteria) / total_criteria) * 100
        
        # Calculate priority score
        amount_score = min(100, scholarship_data.get('amount_per_year', 0) / 500)
        duration_score = scholarship_data.get('duration_years', 1) * 25
        reliability_score = scholarship_data.get('provider_reliability', 70)
        accessibility_score = scholarship_data.get('accessibility_score', 50)
        
        priority_score = (
            amount_score * self.priority_weights['amount'] +
            duration_score * self.priority_weights['duration'] +
            reliability_score * self.priority_weights['provider_reliability'] +
            accessibility_score * self.priority_weights['accessibility']
        )
        
        return ScholarshipMatch(
            scholarship_id=scholarship_data.get('scholarship_id', ''),
            scholarship_name=scholarship_data.get('scholarship_name', ''),
            provider=scholarship_data.get('provider', ''),
            amount_per_year=scholarship_data.get('amount_per_year', 0),
            total_value=scholarship_data.get('total_value', 0),
            duration_years=scholarship_data.get('duration_years', 1),
            match_score=round(match_score, 2),
            eligibility_status=status,
            met_criteria=met_criteria,
            unmet_criteria=unmet_criteria,
            recommendation_priority=int(priority_score * (match_score / 100))
        )
    
    def find_eligible_scholarships(self, student_data: Dict,
                                    scholarship_df: pd.DataFrame) -> List[ScholarshipMatch]:
        """Find all eligible scholarships for a student."""
        matches = []
        
        for _, row in scholarship_df.iterrows():
            match = self.evaluate_scholarship(student_data, row.to_dict())
            matches.append(match)
        
        # Sort by eligibility status and priority
        status_order = {'eligible': 0, 'partial': 1, 'ineligible': 2}
        matches.sort(key=lambda x: (status_order[x.eligibility_status], -x.recommendation_priority))
        
        return matches
    
    def get_eligible_only(self, matches: List[ScholarshipMatch]) -> List[ScholarshipMatch]:
        """Filter to only fully eligible scholarships."""
        return [m for m in matches if m.eligibility_status == 'eligible']
    
    def calculate_potential_savings(self, eligible_scholarships: List[ScholarshipMatch]) -> Dict:
        """Calculate potential financial savings from scholarships."""
        if not eligible_scholarships:
            return {
                'total_potential': 0,
                'per_year_max': 0,
                'scholarship_count': 0,
                'top_scholarship': None
            }
        
        # Note: Student can usually avail only one scholarship
        top = max(eligible_scholarships, key=lambda x: x.total_value)
        
        return {
            'total_potential': top.total_value,
            'per_year_max': top.amount_per_year,
            'scholarship_count': len(eligible_scholarships),
            'top_scholarship': {
                'name': top.scholarship_name,
                'provider': top.provider,
                'amount': top.amount_per_year,
                'total': top.total_value
            },
            'all_eligible_value': sum(s.total_value for s in eligible_scholarships)
        }
    
    def generate_scholarship_report(self, student_data: Dict,
                                     scholarship_df: pd.DataFrame) -> Dict:
        """Generate comprehensive scholarship eligibility report."""
        matches = self.find_eligible_scholarships(student_data, scholarship_df)
        
        eligible = [m for m in matches if m.eligibility_status == 'eligible']
        partial = [m for m in matches if m.eligibility_status == 'partial']
        
        savings = self.calculate_potential_savings(eligible)
        
        return {
            'student_summary': {
                'name': student_data.get('name', 'Unknown'),
                'category': student_data.get('category', 'OC'),
                'income': student_data.get('annual_income', 0),
                'cutoff': student_data.get('cutoff_score', 0),
                'gender': student_data.get('gender', 'Unknown')
            },
            'eligibility_summary': {
                'total_scholarships': len(matches),
                'eligible_count': len(eligible),
                'partial_count': len(partial),
                'ineligible_count': len(matches) - len(eligible) - len(partial)
            },
            'financial_summary': savings,
            'eligible_scholarships': [
                {
                    'name': m.scholarship_name,
                    'provider': m.provider,
                    'amount': m.amount_per_year,
                    'total_value': m.total_value,
                    'criteria_met': m.met_criteria
                }
                for m in eligible
            ],
            'near_miss_scholarships': [
                {
                    'name': m.scholarship_name,
                    'provider': m.provider,
                    'amount': m.amount_per_year,
                    'missing_criteria': m.unmet_criteria
                }
                for m in partial[:5]  # Top 5 near misses
            ],
            'recommendations': self._generate_recommendations(student_data, eligible, partial)
        }
    
    def _generate_recommendations(self, student_data: Dict,
                                   eligible: List[ScholarshipMatch],
                                   partial: List[ScholarshipMatch]) -> List[str]:
        """Generate personalized scholarship recommendations."""
        recommendations = []
        
        if eligible:
            top = max(eligible, key=lambda x: x.total_value)
            recommendations.append(
                f"Apply for {top.scholarship_name} - highest value at ₹{top.total_value:,.0f}"
            )
        
        # Check if improving cutoff would unlock scholarships
        cutoff_blocked = [m for m in partial if 'Cutoff' in str(m.unmet_criteria)]
        if cutoff_blocked:
            recommendations.append(
                f"Improving cutoff could unlock {len(cutoff_blocked)} more scholarships"
            )
        
        # Category-specific recommendations
        category = student_data.get('category', 'OC')
        if category in ['SC', 'ST', 'SCA']:
            recommendations.append(
                "As SC/ST student, prioritize government scholarships with higher amounts"
            )
        elif category in ['BC', 'MBC']:
            recommendations.append(
                "Check BC/MBC specific scholarships from state government"
            )
        
        # Income-based recommendations
        income = student_data.get('annual_income', 0)
        if income < 250000:
            recommendations.append(
                "Low income qualifies for most income-restricted scholarships"
            )
        
        # Gender-specific
        if student_data.get('gender') == 'Female':
            recommendations.append(
                "Apply for girl-specific scholarships like Pragati, Girls Education Scheme"
            )
        
        return recommendations


if __name__ == "__main__":
    # Test scholarship engine
    engine = ScholarshipEngine()
    
    # Test student
    test_student = {
        'name': 'Test Student',
        'category': 'BC',
        'annual_income': 350000,
        'cutoff_score': 185,
        'total_percentage': 88,
        'gender': 'Female'
    }
    
    # Test category eligibility
    is_eligible, reason = engine.check_category_eligibility('BC', 'BC/MBC')
    print(f"Category check: {is_eligible} - {reason}")
    
    # Test income eligibility
    is_eligible, reason = engine.check_income_eligibility(350000, 400000)
    print(f"Income check: {is_eligible} - {reason}")










