"""
District Recommendation Engine
Provides district-based insights and recommendations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DistrictScore:
    """District evaluation score."""
    district_id: str
    district_name: str
    zone: str
    overall_score: float
    education_score: float
    cost_score: float
    accessibility_score: float
    lifestyle_score: float
    recommendation_rank: int
    highlights: List[str]
    considerations: List[str]


class DistrictRecommendationEngine:
    """
    Recommends districts based on student preferences and constraints.
    Analyzes education quality, cost of living, and accessibility.
    """
    
    def __init__(self):
        # Zone characteristics
        self.zone_profiles = {
            'North': {
                'characteristics': ['IT Hub', 'Metro Cities', 'High Competition'],
                'industries': ['IT', 'Automobile', 'Finance'],
                'typical_cost': 'High'
            },
            'South': {
                'characteristics': ['Traditional', 'Temple Towns', 'Agriculture'],
                'industries': ['Agriculture', 'Tourism', 'Textile'],
                'typical_cost': 'Medium'
            },
            'West': {
                'characteristics': ['Industrial', 'Manufacturing Hub'],
                'industries': ['Textile', 'Manufacturing', 'Engineering'],
                'typical_cost': 'Medium-High'
            },
            'Central': {
                'characteristics': ['Educational Hub', 'Historical'],
                'industries': ['Education', 'Agriculture', 'Heavy Industry'],
                'typical_cost': 'Medium'
            }
        }
        
        # Scoring weights
        self.weights = {
            'education': 0.35,
            'cost': 0.25,
            'accessibility': 0.20,
            'lifestyle': 0.20
        }
    
    def calculate_education_score(self, district_data: Dict) -> Tuple[float, List[str]]:
        """Calculate education quality score for a district."""
        score = 0
        highlights = []
        
        # Number of colleges
        num_colleges = district_data.get('num_engineering_colleges', 0)
        if num_colleges >= 20:
            score += 40
            highlights.append(f"Major education hub with {num_colleges} engineering colleges")
        elif num_colleges >= 10:
            score += 30
            highlights.append(f"Good college options ({num_colleges} colleges)")
        elif num_colleges >= 5:
            score += 20
            highlights.append(f"Moderate college options ({num_colleges} colleges)")
        else:
            score += 10
        
        # Government colleges (better value)
        govt_colleges = district_data.get('num_govt_colleges', 0)
        if govt_colleges >= 3:
            score += 25
            highlights.append(f"{govt_colleges} government colleges available")
        elif govt_colleges >= 1:
            score += 15
        
        # Literacy rate as indicator of education culture
        literacy = district_data.get('literacy_rate', 70)
        if literacy >= 85:
            score += 25
            highlights.append(f"High literacy rate ({literacy}%)")
        elif literacy >= 75:
            score += 15
        else:
            score += 5
        
        # Student-friendly rating
        rating = district_data.get('student_friendly_rating', 3)
        score += rating * 5
        
        return min(100, score), highlights
    
    def calculate_cost_score(self, district_data: Dict, student_income: float) -> Tuple[float, List[str]]:
        """Calculate affordability score."""
        monthly_cost = district_data.get('avg_living_cost_monthly', 15000)
        highlights = []
        
        # Base score inversely proportional to cost
        max_cost = 30000  # Reference maximum
        cost_ratio = monthly_cost / max_cost
        base_score = (1 - cost_ratio) * 70
        
        # Adjust based on student's income
        if student_income > 0:
            annual_cost = monthly_cost * 10  # 10 months
            affordability_ratio = annual_cost / student_income
            
            if affordability_ratio <= 0.15:
                base_score += 30
                highlights.append("Very affordable for your budget")
            elif affordability_ratio <= 0.25:
                base_score += 20
                highlights.append("Affordable option")
            elif affordability_ratio <= 0.35:
                base_score += 10
            else:
                highlights.append("May require careful budgeting")
        
        # Cost category info
        if monthly_cost <= 12000:
            highlights.append(f"Low cost of living (₹{monthly_cost:,}/month)")
        elif monthly_cost <= 18000:
            highlights.append(f"Moderate cost of living (₹{monthly_cost:,}/month)")
        else:
            highlights.append(f"Higher cost of living (₹{monthly_cost:,}/month)")
        
        return min(100, max(0, base_score)), highlights
    
    def calculate_accessibility_score(self, district_data: Dict, 
                                       home_district: Optional[str] = None) -> Tuple[float, List[str]]:
        """Calculate accessibility and connectivity score."""
        score = 0
        highlights = []
        
        # Transport connectivity
        connectivity = district_data.get('transport_connectivity', 'Moderate')
        connectivity_scores = {'Excellent': 40, 'Good': 30, 'Moderate': 20, 'Poor': 10}
        score += connectivity_scores.get(connectivity, 20)
        
        if connectivity == 'Excellent':
            highlights.append("Excellent transport connectivity")
        elif connectivity == 'Good':
            highlights.append("Good transport connectivity")
        
        # Airport proximity
        airport = district_data.get('nearest_airport', '')
        if 'International' in str(airport):
            score += 25
            highlights.append(f"International airport nearby")
        elif airport:
            score += 15
        
        # Distance to Chennai (state capital)
        distance = district_data.get('distance_to_chennai_km', 500)
        if distance == 0:
            score += 25
            highlights.append("Located in Chennai - central hub")
        elif distance <= 100:
            score += 20
            highlights.append(f"Close to Chennai ({distance} km)")
        elif distance <= 300:
            score += 15
        else:
            score += 5
        
        return min(100, score), highlights
    
    def calculate_lifestyle_score(self, district_data: Dict,
                                   preferences: Dict) -> Tuple[float, List[str]]:
        """Calculate lifestyle compatibility score."""
        score = 50  # Base score
        highlights = []
        
        # Student-friendly rating
        rating = district_data.get('student_friendly_rating', 3)
        score += (rating - 3) * 15  # Adjust from base
        
        if rating >= 4:
            highlights.append(f"Highly student-friendly (Rating: {rating}/5)")
        
        # Zone match with preferences
        zone = district_data.get('zone', '')
        if preferences.get('preferred_zone'):
            if zone.lower() == preferences['preferred_zone'].lower():
                score += 20
                highlights.append(f"Matches preferred zone ({zone})")
        
        # Major industries (for internship/job opportunities)
        industries = district_data.get('major_industries', '')
        tech_industries = ['IT', 'Technology', 'Software', 'Manufacturing']
        if any(ind in str(industries) for ind in tech_industries):
            score += 15
            highlights.append("Good industry presence for career opportunities")
        
        # Population/urbanization
        population = district_data.get('population', 0)
        if population >= 3000000:
            if preferences.get('urban_preference', True):
                score += 10
                highlights.append("Major urban center")
        elif population < 1500000:
            if not preferences.get('urban_preference', True):
                score += 10
                highlights.append("Smaller, peaceful environment")
        
        return min(100, max(0, score)), highlights
    
    def evaluate_district(self, district_data: Dict, student_data: Dict,
                          preferences: Dict) -> DistrictScore:
        """Evaluate a district for a student."""
        
        # Calculate individual scores
        edu_score, edu_highlights = self.calculate_education_score(district_data)
        cost_score, cost_highlights = self.calculate_cost_score(
            district_data, student_data.get('annual_income', 500000)
        )
        access_score, access_highlights = self.calculate_accessibility_score(
            district_data, student_data.get('home_district')
        )
        life_score, life_highlights = self.calculate_lifestyle_score(
            district_data, preferences
        )
        
        # Weighted overall score
        overall = (
            edu_score * self.weights['education'] +
            cost_score * self.weights['cost'] +
            access_score * self.weights['accessibility'] +
            life_score * self.weights['lifestyle']
        )
        
        # Combine highlights
        all_highlights = edu_highlights + cost_highlights + access_highlights + life_highlights
        
        # Generate considerations (potential downsides)
        considerations = []
        if edu_score < 50:
            considerations.append("Limited college options")
        if cost_score < 50:
            considerations.append("Higher cost of living")
        if access_score < 50:
            considerations.append("Limited connectivity")
        if life_score < 50:
            considerations.append("May need adjustment to lifestyle")
        
        return DistrictScore(
            district_id=district_data.get('district_id', ''),
            district_name=district_data.get('district_name', ''),
            zone=district_data.get('zone', ''),
            overall_score=round(overall, 2),
            education_score=round(edu_score, 2),
            cost_score=round(cost_score, 2),
            accessibility_score=round(access_score, 2),
            lifestyle_score=round(life_score, 2),
            recommendation_rank=0,  # Set later
            highlights=all_highlights[:5],  # Top 5 highlights
            considerations=considerations
        )
    
    def rank_districts(self, district_df: pd.DataFrame, student_data: Dict,
                       preferences: Dict) -> List[DistrictScore]:
        """Rank all districts for a student."""
        scores = []
        
        for _, row in district_df.iterrows():
            score = self.evaluate_district(row.to_dict(), student_data, preferences)
            scores.append(score)
        
        # Sort by overall score
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Assign ranks
        for i, score in enumerate(scores):
            score.recommendation_rank = i + 1
        
        return scores
    
    def get_district_comparison(self, district_df: pd.DataFrame,
                                 district_names: List[str]) -> pd.DataFrame:
        """Compare specific districts side by side."""
        comparison_df = district_df[
            district_df['district_name'].isin(district_names)
        ][['district_name', 'zone', 'num_engineering_colleges', 'num_govt_colleges',
           'avg_living_cost_monthly', 'transport_connectivity', 'literacy_rate',
           'student_friendly_rating', 'education_index', 'livability_score']]
        
        return comparison_df
    
    def get_districts_by_criteria(self, district_df: pd.DataFrame,
                                   criteria: Dict) -> pd.DataFrame:
        """Get districts matching specific criteria."""
        filtered = district_df.copy()
        
        if criteria.get('min_colleges'):
            filtered = filtered[filtered['num_engineering_colleges'] >= criteria['min_colleges']]
        
        if criteria.get('max_cost'):
            filtered = filtered[filtered['avg_living_cost_monthly'] <= criteria['max_cost']]
        
        if criteria.get('min_rating'):
            filtered = filtered[filtered['student_friendly_rating'] >= criteria['min_rating']]
        
        if criteria.get('zone'):
            filtered = filtered[filtered['zone'].str.lower() == criteria['zone'].lower()]
        
        if criteria.get('connectivity'):
            filtered = filtered[filtered['transport_connectivity'].str.lower() == criteria['connectivity'].lower()]
        
        return filtered
    
    def generate_district_insights(self, district_data: Dict) -> Dict:
        """Generate comprehensive insights for a district."""
        zone = district_data.get('zone', 'Unknown')
        zone_profile = self.zone_profiles.get(zone, {})
        
        return {
            'basic_info': {
                'name': district_data.get('district_name', ''),
                'zone': zone,
                'population': district_data.get('population', 0)
            },
            'education': {
                'engineering_colleges': district_data.get('num_engineering_colleges', 0),
                'govt_colleges': district_data.get('num_govt_colleges', 0),
                'literacy_rate': district_data.get('literacy_rate', 0),
                'student_rating': district_data.get('student_friendly_rating', 0)
            },
            'living': {
                'monthly_cost': district_data.get('avg_living_cost_monthly', 0),
                'annual_cost': district_data.get('avg_living_cost_monthly', 0) * 12,
                'cost_category': district_data.get('cost_category', 'Medium')
            },
            'connectivity': {
                'transport': district_data.get('transport_connectivity', 'Moderate'),
                'nearest_airport': district_data.get('nearest_airport', ''),
                'distance_to_chennai': district_data.get('distance_to_chennai_km', 0)
            },
            'opportunities': {
                'major_industries': district_data.get('major_industries', ''),
                'zone_characteristics': zone_profile.get('characteristics', []),
                'typical_industries': zone_profile.get('industries', [])
            },
            'scores': {
                'education_index': district_data.get('education_index', 0),
                'livability_score': district_data.get('livability_score', 0)
            }
        }


if __name__ == "__main__":
    # Test district engine
    engine = DistrictRecommendationEngine()
    
    # Test district data
    test_district = {
        'district_id': 'DIS001',
        'district_name': 'Chennai',
        'zone': 'North',
        'population': 7088000,
        'literacy_rate': 90.33,
        'num_engineering_colleges': 45,
        'num_govt_colleges': 8,
        'avg_living_cost_monthly': 25000,
        'transport_connectivity': 'Excellent',
        'nearest_airport': 'Chennai International',
        'distance_to_chennai_km': 0,
        'major_industries': 'IT/Automobile/Finance',
        'student_friendly_rating': 5
    }
    
    test_student = {
        'annual_income': 600000,
        'home_district': 'Coimbatore'
    }
    
    preferences = {
        'urban_preference': True,
        'preferred_zone': 'North'
    }
    
    # Evaluate
    score = engine.evaluate_district(test_district, test_student, preferences)
    print(f"District: {score.district_name}")
    print(f"Overall Score: {score.overall_score}")
    print(f"Highlights: {score.highlights}")










