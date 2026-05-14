"""
Filtering Engine
Filters colleges based on student eligibility criteria
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class StudentProfile:
    """Student profile for filtering."""
    cutoff_score: float
    category: str
    preferred_branches: List[str]
    preferred_districts: List[str]
    hostel_required: bool
    college_type_preference: Optional[str] = None
    min_placement_rate: float = 0
    max_distance_km: Optional[float] = None


@dataclass
class FilterResult:
    """Result of filtering operation."""
    college_id: str
    college_name: str
    branch_code: str
    branch_name: str
    cutoff: float
    margin: float
    seats_available: int
    district: str
    college_type: str
    match_score: float
    filter_reasons: List[str]


class FilteringEngine:
    """
    Filters colleges based on student eligibility and preferences.
    Uses multi-criteria filtering with priority-based ordering.
    """
    
    def __init__(self):
        # Category hierarchy for reservation
        self.category_hierarchy = {
            'OC': ['OC'],
            'BC': ['BC', 'OC'],
            'BCM': ['BCM', 'BC', 'OC'],
            'MBC': ['MBC', 'BC', 'OC'],
            'DNC': ['DNC', 'MBC', 'BC', 'OC'],
            'SC': ['SC', 'MBC', 'BC', 'OC'],
            'SCA': ['SCA', 'SC', 'MBC', 'BC', 'OC'],
            'ST': ['ST', 'SC', 'MBC', 'BC', 'OC']
        }
        
        # Branch groupings
        self.branch_groups = {
            'computer': ['CS', 'IT', 'AI', 'DS', 'CT'],
            'electronics': ['EC', 'EE', 'EI', 'ET'],
            'mechanical': ['ME', 'AE', 'AU', 'MT'],
            'civil': ['CE', 'AR', 'EN'],
            'chemical': ['CH', 'BT', 'FT', 'PE']
        }
    
    def filter_by_cutoff(self, cutoff_df: pd.DataFrame, student_cutoff: float, 
                         category: str, margin_buffer: float = 0) -> pd.DataFrame:
        """Filter colleges where student's cutoff meets requirements."""
        
        # Get applicable categories based on student's category
        applicable_categories = self.category_hierarchy.get(category, [category])
        
        # Filter by category and cutoff
        filtered = cutoff_df[
            (cutoff_df['category'].isin(applicable_categories)) &
            (cutoff_df['cutoff_2023'] <= (student_cutoff + margin_buffer))
        ].copy()
        
        # Calculate margin
        filtered['margin'] = student_cutoff - filtered['cutoff_2023']
        
        return filtered
    
    def filter_by_branches(self, df: pd.DataFrame, preferred_branches: List[str]) -> pd.DataFrame:
        """Filter and prioritize by preferred branches."""
        if not preferred_branches:
            return df
        
        # Expand branch groups
        expanded_branches = []
        for branch in preferred_branches:
            if branch.lower() in self.branch_groups:
                expanded_branches.extend(self.branch_groups[branch.lower()])
            else:
                expanded_branches.append(branch.upper())
        
        # Filter to preferred branches
        filtered = df[df['branch_code'].isin(expanded_branches)].copy()
        
        # Add priority score based on preference order
        filtered['branch_priority'] = filtered['branch_code'].apply(
            lambda x: expanded_branches.index(x) if x in expanded_branches else len(expanded_branches)
        )
        
        return filtered
    
    def filter_by_district(self, df: pd.DataFrame, college_df: pd.DataFrame,
                           preferred_districts: List[str]) -> pd.DataFrame:
        """Filter by preferred districts."""
        if not preferred_districts or 'Any' in preferred_districts:
            return df
        
        # Case-insensitive district matching
        preferred_lower = [d.lower() for d in preferred_districts]
        
        # Get colleges in preferred districts (case-insensitive)
        district_colleges = college_df[
            college_df['district'].str.lower().isin(preferred_lower)
        ]['college_id'].tolist()
        
        # Filter cutoffs to these colleges
        filtered = df[df['college_id'].isin(district_colleges)].copy()
        
        # If no results found, return original df (let calling code handle it)
        if filtered.empty:
            return df
        
        return filtered
    
    def filter_by_hostel(self, df: pd.DataFrame, college_df: pd.DataFrame,
                         hostel_required: bool) -> pd.DataFrame:
        """Filter by hostel availability."""
        if not hostel_required:
            return df
        
        # Get colleges with hostel - handle both boolean and string values
        hostel_col = college_df['hostel_available']
        if hostel_col.dtype == bool:
            hostel_colleges = college_df[hostel_col == True]['college_id'].tolist()
        else:
            hostel_colleges = college_df[
                hostel_col.astype(str).str.lower().isin(['yes', 'true', '1'])
            ]['college_id'].tolist()
        
        return df[df['college_id'].isin(hostel_colleges)]
    
    def filter_by_college_type(self, df: pd.DataFrame, college_df: pd.DataFrame,
                               college_type: Optional[str]) -> pd.DataFrame:
        """Filter by college type preference."""
        if not college_type:
            return df
        
        type_colleges = college_df[
            college_df['college_type'].str.lower() == college_type.lower()
        ]['college_id'].tolist()
        
        return df[df['college_id'].isin(type_colleges)]
    
    def filter_by_placement(self, df: pd.DataFrame, college_df: pd.DataFrame,
                            min_placement_rate: float) -> pd.DataFrame:
        """Filter by minimum placement rate."""
        if min_placement_rate <= 0:
            return df
        
        placement_colleges = college_df[
            college_df['placement_rate'] >= min_placement_rate
        ]['college_id'].tolist()
        
        return df[df['college_id'].isin(placement_colleges)]
    
    def apply_filters(self, cutoff_df: pd.DataFrame, college_df: pd.DataFrame,
                      student: StudentProfile) -> pd.DataFrame:
        """Apply all filters based on student profile."""
        
        # Start with cutoff filter (mandatory)
        filtered = self.filter_by_cutoff(
            cutoff_df, 
            student.cutoff_score, 
            student.category
        )
        
        if filtered.empty:
            return filtered
        
        # Apply branch filter
        filtered = self.filter_by_branches(filtered, student.preferred_branches)
        
        # Apply district filter
        filtered = self.filter_by_district(filtered, college_df, student.preferred_districts)
        
        # Apply hostel filter
        filtered = self.filter_by_hostel(filtered, college_df, student.hostel_required)
        
        # Apply college type filter
        filtered = self.filter_by_college_type(filtered, college_df, student.college_type_preference)
        
        # Apply placement filter
        filtered = self.filter_by_placement(filtered, college_df, student.min_placement_rate)
        
        return filtered
    
    def get_filter_summary(self, original_count: int, filtered_df: pd.DataFrame) -> Dict:
        """Generate summary of filtering results."""
        return {
            'original_options': original_count,
            'filtered_options': len(filtered_df),
            'reduction_percentage': round((1 - len(filtered_df) / max(original_count, 1)) * 100, 2),
            'colleges_count': filtered_df['college_id'].nunique() if not filtered_df.empty else 0,
            'branches_count': filtered_df['branch_code'].nunique() if not filtered_df.empty else 0,
            'categories_found': filtered_df['category'].unique().tolist() if not filtered_df.empty else []
        }
    
    def get_near_miss_options(self, cutoff_df: pd.DataFrame, student_cutoff: float,
                              category: str, margin: float = 5) -> pd.DataFrame:
        """Get options that are just above student's cutoff (near misses)."""
        applicable_categories = self.category_hierarchy.get(category, [category])
        
        near_miss = cutoff_df[
            (cutoff_df['category'].isin(applicable_categories)) &
            (cutoff_df['cutoff_2023'] > student_cutoff) &
            (cutoff_df['cutoff_2023'] <= student_cutoff + margin)
        ].copy()
        
        near_miss['gap'] = near_miss['cutoff_2023'] - student_cutoff
        
        return near_miss.sort_values('gap')
    
    def get_safe_options(self, cutoff_df: pd.DataFrame, student_cutoff: float,
                         category: str, min_margin: float = 10) -> pd.DataFrame:
        """Get safe options with comfortable margin."""
        applicable_categories = self.category_hierarchy.get(category, [category])
        
        safe = cutoff_df[
            (cutoff_df['category'].isin(applicable_categories)) &
            (cutoff_df['cutoff_2023'] <= student_cutoff - min_margin)
        ].copy()
        
        safe['margin'] = student_cutoff - safe['cutoff_2023']
        
        return safe.sort_values('margin', ascending=False)


def create_student_profile(data: Dict) -> StudentProfile:
    """Helper function to create StudentProfile from dictionary."""
    return StudentProfile(
        cutoff_score=data.get('cutoff_score', 0),
        category=data.get('category', 'OC'),
        preferred_branches=data.get('preferred_branches', []),
        preferred_districts=data.get('preferred_districts', []),
        hostel_required=data.get('hostel_required', False),
        college_type_preference=data.get('college_type_preference'),
        min_placement_rate=data.get('min_placement_rate', 0),
        max_distance_km=data.get('max_distance_km')
    )


if __name__ == "__main__":
    # Test the filtering engine
    import sys
    sys.path.append('..')
    
    engine = FilteringEngine()
    
    # Create test student
    test_student = create_student_profile({
        'cutoff_score': 185,
        'category': 'BC',
        'preferred_branches': ['CS', 'IT', 'EC'],
        'preferred_districts': ['Chennai', 'Coimbatore'],
        'hostel_required': False,
        'min_placement_rate': 70
    })
    
    print(f"Test student profile created: {test_student}")










