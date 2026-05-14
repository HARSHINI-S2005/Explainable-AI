"""
Data Mapper Module
Handles relationships and mappings between datasets
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DataMapper:
    """
    Maps relationships between different datasets.
    Creates lookup tables and relationship mappings.
    """
    
    def __init__(self, processed_data_path: str = "datasets/processed"):
        self.processed_data_path = Path(processed_data_path)
        self.mappings: Dict[str, Dict] = {}
        
    def load_processed_data(self) -> Dict[str, pd.DataFrame]:
        """Load all processed datasets."""
        datasets = {}
        
        files = {
            'college': 'college_processed.csv',
            'cutoff': 'cutoff_processed.csv',
            'student': 'student_processed.csv',
            'district': 'district_processed.csv',
            'scholarship': 'scholarship_processed.csv'
        }
        
        for name, filename in files.items():
            filepath = self.processed_data_path / filename
            if filepath.exists():
                datasets[name] = pd.read_csv(filepath)
        
        return datasets
    
    def create_college_district_mapping(self, college_df: pd.DataFrame, district_df: pd.DataFrame) -> pd.DataFrame:
        """Create mapping between colleges and districts."""
        # Create district lookup
        district_lookup = district_df.set_index('district_name')[
            ['district_id', 'zone', 'education_index', 'livability_score', 
             'avg_living_cost_monthly', 'transport_connectivity']
        ].to_dict('index')
        
        # Map district info to colleges
        college_with_district = college_df.copy()
        
        for col in ['district_id', 'zone', 'education_index', 'livability_score', 
                    'avg_living_cost_monthly', 'transport_connectivity']:
            college_with_district[f'district_{col}'] = college_with_district['district'].map(
                lambda x: district_lookup.get(x, {}).get(col)
            )
        
        self.mappings['college_district'] = {
            'colleges_per_district': college_df.groupby('district').size().to_dict(),
            'district_colleges': college_df.groupby('district')['college_id'].apply(list).to_dict()
        }
        
        return college_with_district
    
    def create_college_branch_mapping(self, college_df: pd.DataFrame, cutoff_df: pd.DataFrame) -> Dict:
        """Create mapping between colleges and their branches."""
        mapping = {}
        
        # Group cutoffs by college
        for college_id in college_df['college_id'].unique():
            college_cutoffs = cutoff_df[cutoff_df['college_id'] == college_id]
            
            mapping[college_id] = {
                'branches': college_cutoffs['branch_code'].unique().tolist(),
                'branch_details': college_cutoffs.groupby('branch_code').agg({
                    'cutoff_2023': 'mean',
                    'seats_available': 'sum',
                    'category': lambda x: x.unique().tolist()
                }).to_dict('index'),
                'total_seats': college_cutoffs['seats_available'].sum(),
                'avg_cutoff': college_cutoffs['cutoff_2023'].mean()
            }
        
        self.mappings['college_branch'] = mapping
        return mapping
    
    def create_category_cutoff_mapping(self, cutoff_df: pd.DataFrame) -> Dict:
        """Create mapping of category-wise cutoffs."""
        mapping = {}
        
        for category in cutoff_df['category'].unique():
            category_data = cutoff_df[cutoff_df['category'] == category]
            
            mapping[category] = {
                'avg_cutoff': category_data['cutoff_2023'].mean(),
                'min_cutoff': category_data['cutoff_2023'].min(),
                'max_cutoff': category_data['cutoff_2023'].max(),
                'total_seats': category_data['seats_available'].sum(),
                'colleges_count': category_data['college_id'].nunique()
            }
        
        self.mappings['category_cutoff'] = mapping
        return mapping
    
    def create_scholarship_eligibility_mapping(self, scholarship_df: pd.DataFrame) -> Dict:
        """Create scholarship eligibility criteria mapping."""
        mapping = {}
        
        for _, row in scholarship_df.iterrows():
            scholarship_id = row['scholarship_id']
            
            mapping[scholarship_id] = {
                'name': row['scholarship_name'],
                'criteria': {
                    'categories': row.get('eligible_categories', ['ALL']),
                    'max_income': row['income_limit'] if row['income_limit'] > 0 else None,
                    'min_cutoff': row['min_cutoff'] if row['min_cutoff'] > 0 else None,
                    'min_percentage': row['min_percentage'] if row['min_percentage'] > 0 else None,
                    'gender': row['gender'] if row['gender'] != 'All' else None
                },
                'benefits': {
                    'amount_per_year': row['amount_per_year'],
                    'duration_years': row['duration_years'],
                    'total_value': row['total_value']
                }
            }
        
        self.mappings['scholarship_eligibility'] = mapping
        return mapping
    
    def create_district_cost_mapping(self, district_df: pd.DataFrame) -> Dict:
        """Create district cost of living mapping."""
        mapping = {}
        
        for _, row in district_df.iterrows():
            mapping[row['district_name']] = {
                'monthly_cost': row['avg_living_cost_monthly'],
                'yearly_cost': row['avg_living_cost_monthly'] * 12,
                'cost_category': row.get('cost_category', 'Medium'),
                'livability_score': row['livability_score']
            }
        
        self.mappings['district_cost'] = mapping
        return mapping
    
    def create_branch_college_ranking(self, college_df: pd.DataFrame, cutoff_df: pd.DataFrame) -> Dict:
        """Create branch-wise college rankings."""
        mapping = {}
        
        # Merge college and cutoff data
        merged = cutoff_df.merge(
            college_df[['college_id', 'college_name', 'overall_score', 'placement_rate']],
            on='college_id'
        )
        
        for branch in cutoff_df['branch_code'].unique():
            branch_data = merged[merged['branch_code'] == branch].copy()
            
            # Calculate branch-specific ranking score
            branch_data['branch_rank_score'] = (
                branch_data['overall_score'] * 0.4 +
                branch_data['placement_rate'] * 0.3 +
                (200 - branch_data['cutoff_2023']) * 0.3  # Higher cutoff = better college
            )
            
            # Sort and rank
            branch_data = branch_data.sort_values('branch_rank_score', ascending=False)
            branch_data['branch_rank'] = range(1, len(branch_data) + 1)
            
            mapping[branch] = {
                'rankings': branch_data[['college_id', 'college_name', 'branch_rank', 'cutoff_2023']].to_dict('records'),
                'top_colleges': branch_data.head(10)['college_name'].tolist(),
                'avg_cutoff': branch_data['cutoff_2023'].mean(),
                'total_seats': branch_data['seats_available'].sum()
            }
        
        self.mappings['branch_college_ranking'] = mapping
        return mapping
    
    def get_student_eligible_colleges(self, student_data: Dict, college_df: pd.DataFrame, 
                                       cutoff_df: pd.DataFrame) -> List[Dict]:
        """Get list of eligible colleges for a student."""
        cutoff_score = student_data.get('cutoff_score', 0)
        category = student_data.get('category', 'OC')
        preferred_branches = student_data.get('preferred_branches', [])
        preferred_district = student_data.get('preferred_district')
        hostel_required = student_data.get('hostel_required', False)
        
        # Filter cutoffs based on student's score and category
        eligible_cutoffs = cutoff_df[
            (cutoff_df['cutoff_2023'] <= cutoff_score) &
            (cutoff_df['category'] == category)
        ]
        
        # If preferred branches specified, prioritize them
        if preferred_branches:
            eligible_cutoffs['branch_priority'] = eligible_cutoffs['branch_code'].apply(
                lambda x: preferred_branches.index(x) if x in preferred_branches else 999
            )
            eligible_cutoffs = eligible_cutoffs.sort_values('branch_priority')
        
        # Merge with college data
        eligible_colleges = eligible_cutoffs.merge(college_df, on='college_id')
        
        # Apply district filter if specified
        if preferred_district and preferred_district != 'Any':
            eligible_colleges = eligible_colleges[
                eligible_colleges['district'] == preferred_district
            ]
        
        # Apply hostel filter
        if hostel_required:
            eligible_colleges = eligible_colleges[
                eligible_colleges['hostel_available'].str.lower() == 'yes'
            ]
        
        # Prepare result
        result = []
        for _, row in eligible_colleges.iterrows():
            result.append({
                'college_id': row['college_id'],
                'college_name': row['college_name'],
                'branch': row['branch_name'],
                'branch_code': row['branch_code'],
                'cutoff': row['cutoff_2023'],
                'margin': round(cutoff_score - row['cutoff_2023'], 2),
                'seats': row['seats_available'],
                'district': row['district'],
                'college_score': row.get('overall_score', 0)
            })
        
        # Sort by college score
        result.sort(key=lambda x: x['college_score'], reverse=True)
        
        return result
    
    def get_student_eligible_scholarships(self, student_data: Dict, scholarship_df: pd.DataFrame) -> List[Dict]:
        """Get list of eligible scholarships for a student."""
        category = student_data.get('category', 'OC')
        annual_income = student_data.get('annual_income', 0)
        cutoff_score = student_data.get('cutoff_score', 0)
        percentage = student_data.get('total_percentage', 0)
        gender = student_data.get('gender', 'Male')
        
        eligible = []
        
        for _, row in scholarship_df.iterrows():
            is_eligible = True
            eligibility_reasons = []
            
            # Check category eligibility
            if row['category_eligible'] != 'ALL':
                eligible_cats = [c.strip() for c in str(row['category_eligible']).split('/')]
                if category not in eligible_cats and 'All' not in eligible_cats:
                    is_eligible = False
                    eligibility_reasons.append(f"Category {category} not eligible")
            
            # Check income limit
            if row['income_limit'] > 0 and annual_income > row['income_limit']:
                is_eligible = False
                eligibility_reasons.append(f"Income exceeds limit of {row['income_limit']}")
            
            # Check minimum cutoff
            if row['min_cutoff'] > 0 and cutoff_score < row['min_cutoff']:
                is_eligible = False
                eligibility_reasons.append(f"Cutoff below minimum {row['min_cutoff']}")
            
            # Check minimum percentage
            if row['min_percentage'] > 0 and percentage < row['min_percentage']:
                is_eligible = False
                eligibility_reasons.append(f"Percentage below minimum {row['min_percentage']}")
            
            # Check gender
            if row['gender'] != 'All' and row['gender'] != gender:
                is_eligible = False
                eligibility_reasons.append(f"Gender restriction: {row['gender']} only")
            
            if is_eligible:
                eligible.append({
                    'scholarship_id': row['scholarship_id'],
                    'name': row['scholarship_name'],
                    'provider': row['provider'],
                    'amount_per_year': row['amount_per_year'],
                    'total_value': row['total_value'],
                    'duration_years': row['duration_years'],
                    'attractiveness_score': row.get('attractiveness_score', 0)
                })
        
        # Sort by attractiveness score
        eligible.sort(key=lambda x: x['attractiveness_score'], reverse=True)
        
        return eligible
    
    def create_all_mappings(self) -> Dict:
        """Create all mappings and return summary."""
        datasets = self.load_processed_data()
        
        if 'college' in datasets and 'district' in datasets:
            self.create_college_district_mapping(datasets['college'], datasets['district'])
        
        if 'college' in datasets and 'cutoff' in datasets:
            self.create_college_branch_mapping(datasets['college'], datasets['cutoff'])
            self.create_branch_college_ranking(datasets['college'], datasets['cutoff'])
        
        if 'cutoff' in datasets:
            self.create_category_cutoff_mapping(datasets['cutoff'])
        
        if 'scholarship' in datasets:
            self.create_scholarship_eligibility_mapping(datasets['scholarship'])
        
        if 'district' in datasets:
            self.create_district_cost_mapping(datasets['district'])
        
        return {
            'mappings_created': list(self.mappings.keys()),
            'total_mappings': len(self.mappings)
        }


if __name__ == "__main__":
    # Test the mapper
    mapper = DataMapper()
    result = mapper.create_all_mappings()
    print(f"Created mappings: {result['mappings_created']}")
    
    # Test student eligibility
    test_student = {
        'cutoff_score': 185,
        'category': 'OC',
        'preferred_branches': ['CS', 'IT', 'EC'],
        'preferred_district': 'Chennai',
        'hostel_required': False,
        'annual_income': 500000,
        'total_percentage': 85,
        'gender': 'Male'
    }
    
    datasets = mapper.load_processed_data()
    if 'college' in datasets and 'cutoff' in datasets:
        eligible_colleges = mapper.get_student_eligible_colleges(
            test_student, datasets['college'], datasets['cutoff']
        )
        print(f"\nEligible colleges for test student: {len(eligible_colleges)}")
        for college in eligible_colleges[:5]:
            print(f"  - {college['college_name']} ({college['branch']}): Cutoff {college['cutoff']}")










