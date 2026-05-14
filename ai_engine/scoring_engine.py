"""
Scoring Engine
Calculates match scores between students and colleges
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ScoringWeights:
    """Configurable weights for scoring."""
    cutoff_match: float = 0.25
    branch_preference: float = 0.20
    college_quality: float = 0.20
    placement: float = 0.15
    location: float = 0.10
    cost: float = 0.10


class ScoringEngine:
    """
    Calculates comprehensive match scores for college recommendations.
    Uses weighted multi-factor scoring algorithm.
    """
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        
        # Branch demand scores (higher = more demand)
        self.branch_demand = {
            'CS': 100, 'AI': 100, 'DS': 95,
            'IT': 90, 'EC': 85, 'EE': 75,
            'ME': 70, 'CE': 60, 'CH': 55,
            'BT': 50, 'AE': 65, 'MT': 45
        }
        
        # College type scores
        self.college_type_scores = {
            'Government': 100,
            'Private Aided': 80,
            'Private': 60
        }
        
        # Accreditation scores
        self.accreditation_scores = {
            'NAAC A++': 100,
            'NAAC A+': 85,
            'NAAC A': 70,
            'NAAC B++': 55,
            'NAAC B+': 40,
            'NAAC B': 25
        }
    
    def calculate_cutoff_score(self, student_cutoff: float, college_cutoff: float,
                                max_cutoff: float = 200) -> float:
        """
        Calculate cutoff match score.
        Higher score for cutoffs closer to (but below) student's score.
        """
        if college_cutoff > student_cutoff:
            return 0
        
        margin = student_cutoff - college_cutoff
        
        # Optimal margin is 5-15 points (not too safe, not too risky)
        if 5 <= margin <= 15:
            base_score = 100
        elif margin < 5:
            # Risky choice
            base_score = 70 + (margin * 6)  # 70-100
        else:
            # Safe choice (diminishing returns after 15)
            base_score = max(50, 100 - (margin - 15) * 2)
        
        # Normalize to 0-100
        return min(100, max(0, base_score))
    
    def calculate_branch_preference_score(self, branch_code: str, 
                                          preferred_branches: List[str]) -> float:
        """Calculate score based on branch preference order."""
        if not preferred_branches:
            # No preference - use demand score
            return self.branch_demand.get(branch_code, 50)
        
        if branch_code in preferred_branches:
            # Position-based scoring
            position = preferred_branches.index(branch_code)
            return max(50, 100 - (position * 20))
        
        return 30  # Not in preferences
    
    def calculate_college_quality_score(self, college_data: Dict) -> float:
        """Calculate college quality score based on multiple factors."""
        score = 0
        
        # Ranking score (inverse - lower rank is better)
        ranking = college_data.get('ranking', 100)
        ranking_score = max(0, 100 - ranking)
        score += ranking_score * 0.3
        
        # College type score
        college_type = college_data.get('college_type', 'Private')
        type_score = self.college_type_scores.get(college_type, 50)
        score += type_score * 0.25
        
        # Accreditation score
        accreditation = college_data.get('accreditation', '')
        # Normalize accreditation string
        for key in self.accreditation_scores:
            if key.lower() in str(accreditation).lower():
                score += self.accreditation_scores[key] * 0.25
                break
        else:
            score += 30 * 0.25
        
        # Overall score from data
        overall = college_data.get('overall_score', 50)
        score += min(100, overall) * 0.2
        
        return min(100, score)
    
    def calculate_placement_score(self, placement_rate: float, 
                                   avg_package: float) -> float:
        """Calculate placement-based score."""
        # Placement rate score (0-100%)
        placement_score = min(100, placement_rate)
        
        # Package score (normalized, assuming max 20 LPA)
        package_score = min(100, avg_package * 5)  # 20 LPA = 100
        
        # Weighted combination
        return (placement_score * 0.6 + package_score * 0.4)
    
    def calculate_location_score(self, college_district: str, 
                                  preferred_districts: List[str],
                                  district_data: Optional[Dict] = None) -> float:
        """Calculate location preference score."""
        score = 50  # Base score
        
        # District preference
        if preferred_districts and 'Any' not in preferred_districts:
            if college_district in preferred_districts:
                position = preferred_districts.index(college_district)
                score = max(60, 100 - (position * 15))
            else:
                score = 30
        
        # Add district quality factors if available
        if district_data:
            livability = district_data.get('livability_score', 50)
            connectivity = district_data.get('accessibility_score', 50)
            score = (score * 0.5 + livability * 0.25 + connectivity * 0.25)
        
        return min(100, score)
    
    def calculate_cost_score(self, college_type: str, district_cost: float,
                              student_income: float) -> float:
        """Calculate affordability score."""
        # Estimate annual cost
        tuition_estimate = {
            'Government': 50000,
            'Private Aided': 100000,
            'Private': 200000
        }
        
        tuition = tuition_estimate.get(college_type, 150000)
        total_annual = tuition + (district_cost * 10)  # 10 months
        
        # Compare with student's family income
        if student_income <= 0:
            return 50  # Unknown income
        
        cost_ratio = total_annual / student_income
        
        if cost_ratio <= 0.2:
            return 100  # Very affordable
        elif cost_ratio <= 0.4:
            return 80
        elif cost_ratio <= 0.6:
            return 60
        elif cost_ratio <= 0.8:
            return 40
        else:
            return 20  # Expensive
    
    def calculate_total_score(self, student_data: Dict, college_data: Dict,
                               cutoff_data: Dict, district_data: Optional[Dict] = None) -> Dict:
        """Calculate comprehensive match score."""
        
        # Individual scores
        cutoff_score = self.calculate_cutoff_score(
            student_data.get('cutoff_score', 0),
            cutoff_data.get('cutoff_2023', 200)
        )
        
        branch_score = self.calculate_branch_preference_score(
            cutoff_data.get('branch_code', ''),
            student_data.get('preferred_branches', [])
        )
        
        quality_score = self.calculate_college_quality_score(college_data)
        
        placement_score = self.calculate_placement_score(
            college_data.get('placement_rate', 0),
            college_data.get('avg_package_lpa', 0)
        )
        
        location_score = self.calculate_location_score(
            college_data.get('district', ''),
            student_data.get('preferred_districts', []),
            district_data
        )
        
        cost_score = self.calculate_cost_score(
            college_data.get('college_type', 'Private'),
            district_data.get('avg_living_cost_monthly', 15000) if district_data else 15000,
            student_data.get('annual_income', 500000)
        )
        
        # Weighted total
        total_score = (
            cutoff_score * self.weights.cutoff_match +
            branch_score * self.weights.branch_preference +
            quality_score * self.weights.college_quality +
            placement_score * self.weights.placement +
            location_score * self.weights.location +
            cost_score * self.weights.cost
        )
        
        return {
            'total_score': round(total_score, 2),
            'breakdown': {
                'cutoff_match': round(cutoff_score, 2),
                'branch_preference': round(branch_score, 2),
                'college_quality': round(quality_score, 2),
                'placement': round(placement_score, 2),
                'location': round(location_score, 2),
                'cost': round(cost_score, 2)
            },
            'weights': {
                'cutoff_match': self.weights.cutoff_match,
                'branch_preference': self.weights.branch_preference,
                'college_quality': self.weights.college_quality,
                'placement': self.weights.placement,
                'location': self.weights.location,
                'cost': self.weights.cost
            }
        }
    
    def score_all_options(self, student_data: Dict, filtered_cutoffs: pd.DataFrame,
                          college_df: pd.DataFrame, district_df: pd.DataFrame) -> List[Dict]:
        """Score all filtered options and return ranked list."""
        scored_options = []
        
        # Create lookup dictionaries
        college_lookup = college_df.set_index('college_id').to_dict('index')
        district_lookup = district_df.set_index('district_name').to_dict('index')
        
        for _, cutoff_row in filtered_cutoffs.iterrows():
            college_id = cutoff_row['college_id']
            college_data = college_lookup.get(college_id, {})
            district_name = college_data.get('district', '')
            district_data = district_lookup.get(district_name, {})
            
            # Calculate score
            score_result = self.calculate_total_score(
                student_data,
                college_data,
                cutoff_row.to_dict(),
                district_data
            )
            
            # Build result
            scored_options.append({
                'college_id': college_id,
                'college_name': college_data.get('college_name', 'Unknown'),
                'branch_code': cutoff_row['branch_code'],
                'branch_name': cutoff_row['branch_name'],
                'cutoff': cutoff_row['cutoff_2023'],
                'margin': student_data['cutoff_score'] - cutoff_row['cutoff_2023'],
                'seats': cutoff_row['seats_available'],
                'district': district_name,
                'college_type': college_data.get('college_type', ''),
                'placement_rate': college_data.get('placement_rate', 0),
                'total_score': score_result['total_score'],
                'score_breakdown': score_result['breakdown']
            })
        
        # Sort by total score
        scored_options.sort(key=lambda x: x['total_score'], reverse=True)
        
        return scored_options
    
    def get_score_explanation(self, score_result: Dict) -> str:
        """Generate human-readable explanation of score."""
        breakdown = score_result['breakdown']
        
        explanations = []
        
        if breakdown['cutoff_match'] >= 80:
            explanations.append("Excellent cutoff match - high admission probability")
        elif breakdown['cutoff_match'] >= 60:
            explanations.append("Good cutoff match - reasonable admission chance")
        else:
            explanations.append("Tight cutoff match - competitive admission")
        
        if breakdown['branch_preference'] >= 80:
            explanations.append("Top branch preference matched")
        
        if breakdown['college_quality'] >= 80:
            explanations.append("High-quality institution")
        
        if breakdown['placement'] >= 80:
            explanations.append("Excellent placement record")
        
        if breakdown['location'] >= 80:
            explanations.append("Preferred location")
        
        if breakdown['cost'] >= 80:
            explanations.append("Affordable option")
        
        return " | ".join(explanations)


if __name__ == "__main__":
    # Test scoring engine
    engine = ScoringEngine()
    
    # Test individual scoring functions
    cutoff_score = engine.calculate_cutoff_score(185, 180)
    print(f"Cutoff score (185 vs 180): {cutoff_score}")
    
    branch_score = engine.calculate_branch_preference_score('CS', ['CS', 'IT', 'EC'])
    print(f"Branch score (CS in [CS, IT, EC]): {branch_score}")
    
    quality_score = engine.calculate_college_quality_score({
        'ranking': 5,
        'college_type': 'Government',
        'accreditation': 'NAAC A++',
        'overall_score': 90
    })
    print(f"Quality score: {quality_score}")










