"""
Recommendation Engine
Main engine that orchestrates all AI components for final recommendations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import json

from .filtering_engine import FilteringEngine, StudentProfile, create_student_profile
from .scoring_engine import ScoringEngine, ScoringWeights
from .scholarship_engine import ScholarshipEngine
from .district_engine import DistrictRecommendationEngine


@dataclass
class CollegeRecommendation:
    """Final college recommendation."""
    rank: int
    college_id: str
    college_name: str
    branch_code: str
    branch_name: str
    district: str
    college_type: str
    cutoff: float
    margin: float
    seats_available: int
    total_score: float
    score_breakdown: Dict
    admission_probability: str
    highlights: List[str]


@dataclass
class RecommendationResult:
    """Complete recommendation result for a student."""
    student_id: str
    student_name: str
    cutoff_score: float
    category: str
    total_recommendations: int
    recommendations: List[CollegeRecommendation]
    scholarship_summary: Dict
    district_recommendations: List[Dict]
    insights: Dict


class RecommendationEngine:
    """
    Master recommendation engine that combines all AI components
    to provide comprehensive college recommendations.
    """
    
    def __init__(self, data_path: str = "datasets/processed"):
        self.data_path = Path(data_path)
        
        # Initialize sub-engines
        self.filtering_engine = FilteringEngine()
        self.scoring_engine = ScoringEngine()
        self.scholarship_engine = ScholarshipEngine()
        self.district_engine = DistrictRecommendationEngine()
        
        # Load datasets
        self.datasets = self._load_datasets()
    
    def _load_datasets(self) -> Dict[str, pd.DataFrame]:
        """Load all processed datasets."""
        datasets = {}
        
        files = {
            'college': 'college_processed.csv',
            'cutoff': 'cutoff_processed.csv',
            'district': 'district_processed.csv',
            'scholarship': 'scholarship_processed.csv'
        }
        
        for name, filename in files.items():
            filepath = self.data_path / filename
            if filepath.exists():
                datasets[name] = pd.read_csv(filepath)
        
        return datasets
    
    def _calculate_admission_probability(self, margin: float, seats: int,
                                          competition_intensity: float) -> str:
        """Estimate admission probability based on margin and competition."""
        if margin >= 15 and seats >= 50:
            return "Very High (>90%)"
        elif margin >= 10 and seats >= 30:
            return "High (75-90%)"
        elif margin >= 5 and seats >= 20:
            return "Good (60-75%)"
        elif margin >= 0:
            return "Moderate (40-60%)"
        else:
            return "Low (<40%)"
    
    def _generate_highlights(self, college_data: Dict, cutoff_data: Dict,
                              score_breakdown: Dict) -> List[str]:
        """Generate highlights for a recommendation."""
        highlights = []
        
        # Placement highlight
        placement = college_data.get('placement_rate', 0)
        if placement >= 90:
            highlights.append(f"Excellent placements ({placement}%)")
        elif placement >= 80:
            highlights.append(f"Strong placements ({placement}%)")
        
        # Package highlight
        package = college_data.get('avg_package_lpa', 0)
        if package >= 10:
            highlights.append(f"High avg package (₹{package}L)")
        elif package >= 7:
            highlights.append(f"Good avg package (₹{package}L)")
        
        # College type
        if college_data.get('college_type') == 'Government':
            highlights.append("Government college - Lower fees")
        
        # Accreditation
        accred = college_data.get('accreditation', '')
        if 'A++' in str(accred):
            highlights.append("NAAC A++ Accredited")
        elif 'A+' in str(accred):
            highlights.append("NAAC A+ Accredited")
        
        # Score-based highlights
        if score_breakdown.get('cutoff_match', 0) >= 90:
            highlights.append("Excellent cutoff match")
        if score_breakdown.get('location', 0) >= 80:
            highlights.append("Preferred location")
        
        return highlights[:4]  # Max 4 highlights
    
    def generate_recommendations(self, student_data: Dict,
                                  preferences: Optional[Dict] = None,
                                  max_recommendations: int = 20) -> RecommendationResult:
        """Generate comprehensive recommendations for a student."""
        
        preferences = preferences or {}
        
        # Create student profile
        profile_data = {
            'cutoff_score': student_data.get('cutoff_score', 0),
            'category': student_data.get('category', 'OC'),
            'preferred_branches': student_data.get('preferred_branches', 
                                   preferences.get('preferred_branches', [])),
            'preferred_districts': student_data.get('preferred_districts',
                                    preferences.get('preferred_districts', [])),
            'hostel_required': student_data.get('hostel_required',
                               preferences.get('hostel_required', False)),
            'college_type_preference': preferences.get('college_type'),
            'min_placement_rate': preferences.get('min_placement_rate', 0)
        }
        
        student_profile = create_student_profile(profile_data)
        
        # Step 1: Filter eligible colleges
        filtered_cutoffs = self.filtering_engine.apply_filters(
            self.datasets['cutoff'],
            self.datasets['college'],
            student_profile
        )
        
        if filtered_cutoffs.empty:
            # Try with relaxed filters
            filtered_cutoffs = self.filtering_engine.filter_by_cutoff(
                self.datasets['cutoff'],
                student_data['cutoff_score'],
                student_data['category'],
                margin_buffer=5
            )
        
        # Step 2: Score all options
        scored_options = self.scoring_engine.score_all_options(
            student_data,
            filtered_cutoffs,
            self.datasets['college'],
            self.datasets['district']
        )
        
        # Step 3: Create recommendation objects
        recommendations = []
        college_lookup = self.datasets['college'].set_index('college_id').to_dict('index')
        cutoff_lookup = self.datasets['cutoff'].set_index(['college_id', 'branch_code']).to_dict('index')
        
        for i, option in enumerate(scored_options[:max_recommendations]):
            college_data = college_lookup.get(option['college_id'], {})
            
            # Get competition intensity from cutoff data
            cutoff_key = (option['college_id'], option['branch_code'])
            cutoff_info = cutoff_lookup.get(cutoff_key, {})
            competition = cutoff_info.get('competition_intensity', 50)
            
            rec = CollegeRecommendation(
                rank=i + 1,
                college_id=option['college_id'],
                college_name=option['college_name'],
                branch_code=option['branch_code'],
                branch_name=option['branch_name'],
                district=option['district'],
                college_type=option['college_type'],
                cutoff=option['cutoff'],
                margin=round(option['margin'], 2),
                seats_available=option['seats'],
                total_score=option['total_score'],
                score_breakdown=option['score_breakdown'],
                admission_probability=self._calculate_admission_probability(
                    option['margin'], option['seats'], competition
                ),
                highlights=self._generate_highlights(
                    college_data, cutoff_info, option['score_breakdown']
                )
            )
            recommendations.append(rec)
        
        # Step 4: Get scholarship information
        scholarship_report = self.scholarship_engine.generate_scholarship_report(
            student_data, self.datasets['scholarship']
        )
        
        # Step 5: Get district recommendations
        district_scores = self.district_engine.rank_districts(
            self.datasets['district'],
            student_data,
            preferences
        )
        
        district_recs = [
            {
                'rank': ds.recommendation_rank,
                'district': ds.district_name,
                'zone': ds.zone,
                'score': ds.overall_score,
                'highlights': ds.highlights
            }
            for ds in district_scores[:5]
        ]
        
        # Step 6: Generate insights
        insights = self._generate_insights(
            student_data, recommendations, scholarship_report, district_scores
        )
        
        return RecommendationResult(
            student_id=student_data.get('student_id', ''),
            student_name=student_data.get('name', 'Unknown'),
            cutoff_score=student_data.get('cutoff_score', 0),
            category=student_data.get('category', 'OC'),
            total_recommendations=len(recommendations),
            recommendations=recommendations,
            scholarship_summary=scholarship_report['financial_summary'],
            district_recommendations=district_recs,
            insights=insights
        )
    
    def _generate_insights(self, student_data: Dict, 
                           recommendations: List[CollegeRecommendation],
                           scholarship_report: Dict,
                           district_scores: List) -> Dict:
        """Generate personalized insights."""
        insights = {
            'admission_outlook': '',
            'top_picks': [],
            'financial_advice': [],
            'strategic_tips': []
        }
        
        cutoff = student_data.get('cutoff_score', 0)
        
        # Admission outlook
        if cutoff >= 195:
            insights['admission_outlook'] = "Excellent position - Top colleges within reach"
        elif cutoff >= 185:
            insights['admission_outlook'] = "Strong position - Good college options available"
        elif cutoff >= 175:
            insights['admission_outlook'] = "Competitive position - Strategic choices recommended"
        elif cutoff >= 165:
            insights['admission_outlook'] = "Moderate position - Focus on tier-2 colleges"
        else:
            insights['admission_outlook'] = "Limited options in preferred branches - Consider alternatives"
        
        # Top picks analysis
        if recommendations:
            top_3 = recommendations[:3]
            for rec in top_3:
                insights['top_picks'].append({
                    'college': rec.college_name,
                    'branch': rec.branch_name,
                    'why': f"Score: {rec.total_score}, Probability: {rec.admission_probability}"
                })
        
        # Financial advice
        scholarship_count = scholarship_report.get('eligibility_summary', {}).get('eligible_count', 0)
        scholarship_value = scholarship_report.get('financial_summary', {}).get('total_potential', 0)
        
        if scholarship_count > 0:
            insights['financial_advice'].append(
                f"Eligible for {scholarship_count} scholarships worth up to ₹{scholarship_value:,.0f}"
            )
        
        # Recommend government colleges if income is low
        if student_data.get('annual_income', 0) < 400000:
            insights['financial_advice'].append(
                "Consider government colleges for lower fees"
            )
        
        # Strategic tips
        category = student_data.get('category', 'OC')
        if category in ['SC', 'ST']:
            insights['strategic_tips'].append(
                "Reservation benefits available - Include reach colleges in choices"
            )
        
        # Branch-specific advice
        if cutoff >= 190:
            insights['strategic_tips'].append(
                "Strong cutoff - Can aim for CS/AI in top colleges"
            )
        elif cutoff >= 180:
            insights['strategic_tips'].append(
                "Consider ECE/IT as alternatives to CS for better college quality"
            )
        
        # District advice
        if district_scores:
            top_district = district_scores[0]
            insights['strategic_tips'].append(
                f"Top recommended district: {top_district.district_name} ({top_district.zone} zone)"
            )
        
        return insights
    
    def get_quick_recommendations(self, cutoff_score: float, category: str,
                                   branch_preferences: List[str],
                                   limit: int = 10) -> List[Dict]:
        """Get quick recommendations without full analysis."""
        student_data = {
            'cutoff_score': cutoff_score,
            'category': category,
            'preferred_branches': branch_preferences
        }
        
        profile = create_student_profile(student_data)
        
        # Filter
        filtered = self.filtering_engine.apply_filters(
            self.datasets['cutoff'],
            self.datasets['college'],
            profile
        )
        
        # Quick scoring
        results = []
        college_lookup = self.datasets['college'].set_index('college_id').to_dict('index')
        
        for _, row in filtered.head(limit * 2).iterrows():
            college = college_lookup.get(row['college_id'], {})
            margin = cutoff_score - row['cutoff_2023']
            
            results.append({
                'college': college.get('college_name', 'Unknown'),
                'branch': row['branch_name'],
                'cutoff': row['cutoff_2023'],
                'margin': round(margin, 2),
                'seats': row['seats_available'],
                'type': college.get('college_type', ''),
                'placement': college.get('placement_rate', 0)
            })
        
        # Sort by margin (prefer optimal margin)
        results.sort(key=lambda x: abs(x['margin'] - 10))
        
        return results[:limit]
    
    def compare_colleges(self, college_ids: List[str], student_data: Dict) -> List[Dict]:
        """Compare specific colleges for a student."""
        comparisons = []
        
        college_df = self.datasets['college']
        cutoff_df = self.datasets['cutoff']
        district_df = self.datasets['district']
        
        for college_id in college_ids:
            college_row = college_df[college_df['college_id'] == college_id]
            if college_row.empty:
                continue
            
            college_data = college_row.iloc[0].to_dict()
            college_cutoffs = cutoff_df[cutoff_df['college_id'] == college_id]
            
            # Find best matching branch
            category = student_data.get('category', 'OC')
            matching = college_cutoffs[college_cutoffs['category'] == category]
            
            if matching.empty:
                matching = college_cutoffs
            
            # Get district data
            district_name = college_data.get('district', '')
            district_row = district_df[district_df['district_name'] == district_name]
            district_data = district_row.iloc[0].to_dict() if not district_row.empty else {}
            
            for _, cutoff_row in matching.iterrows():
                score_result = self.scoring_engine.calculate_total_score(
                    student_data,
                    college_data,
                    cutoff_row.to_dict(),
                    district_data
                )
                
                comparisons.append({
                    'college_id': college_id,
                    'college_name': college_data.get('college_name'),
                    'branch': cutoff_row['branch_name'],
                    'cutoff': cutoff_row['cutoff_2023'],
                    'margin': student_data.get('cutoff_score', 0) - cutoff_row['cutoff_2023'],
                    'total_score': score_result['total_score'],
                    'breakdown': score_result['breakdown'],
                    'placement_rate': college_data.get('placement_rate'),
                    'avg_package': college_data.get('avg_package_lpa'),
                    'college_type': college_data.get('college_type'),
                    'district': district_name
                })
        
        return sorted(comparisons, key=lambda x: x['total_score'], reverse=True)
    
    def to_json(self, result: RecommendationResult) -> str:
        """Convert recommendation result to JSON."""
        data = {
            'student_id': result.student_id,
            'student_name': result.student_name,
            'cutoff_score': result.cutoff_score,
            'category': result.category,
            'total_recommendations': result.total_recommendations,
            'recommendations': [asdict(r) for r in result.recommendations],
            'scholarship_summary': result.scholarship_summary,
            'district_recommendations': result.district_recommendations,
            'insights': result.insights
        }
        return json.dumps(data, indent=2)


# Convenience function for quick access
def get_recommendations(student_data: Dict, preferences: Optional[Dict] = None) -> RecommendationResult:
    """Convenience function to get recommendations."""
    engine = RecommendationEngine()
    return engine.generate_recommendations(student_data, preferences)


if __name__ == "__main__":
    # Test the recommendation engine
    engine = RecommendationEngine()
    
    test_student = {
        'student_id': 'TEST001',
        'name': 'Test Student',
        'cutoff_score': 185,
        'category': 'BC',
        'annual_income': 450000,
        'total_percentage': 85,
        'gender': 'Male',
        'preferred_branches': ['CS', 'IT', 'EC'],
        'preferred_districts': ['Chennai', 'Coimbatore'],
        'hostel_required': True
    }
    
    preferences = {
        'min_placement_rate': 70,
        'college_type': None
    }
    
    print("Generating recommendations...")
    result = engine.generate_recommendations(test_student, preferences)
    
    print(f"\n=== Recommendations for {result.student_name} ===")
    print(f"Cutoff: {result.cutoff_score} | Category: {result.category}")
    print(f"Total Options: {result.total_recommendations}")
    
    print("\nTop 5 Recommendations:")
    for rec in result.recommendations[:5]:
        print(f"  {rec.rank}. {rec.college_name} - {rec.branch_name}")
        print(f"     Cutoff: {rec.cutoff} | Margin: {rec.margin} | Score: {rec.total_score}")
        print(f"     Probability: {rec.admission_probability}")
        print(f"     Highlights: {', '.join(rec.highlights)}")
    
    print(f"\nScholarship Potential: ₹{result.scholarship_summary.get('total_potential', 0):,.0f}")
    
    print("\nInsights:")
    print(f"  Outlook: {result.insights['admission_outlook']}")










