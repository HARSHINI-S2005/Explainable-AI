"""
Data Preprocessor Module
Handles feature engineering and data transformation
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler


class DataPreprocessor:
    """
    Preprocesses cleaned data for AI model consumption.
    Handles feature engineering, encoding, and normalization.
    """
    
    def __init__(self, cleaned_data_path: str = "datasets/cleaned", processed_data_path: str = "datasets/processed"):
        self.cleaned_data_path = Path(cleaned_data_path)
        self.processed_data_path = Path(processed_data_path)
        self.processed_data_path.mkdir(parents=True, exist_ok=True)
        
        # Encoders and scalers
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        
        # Category hierarchy for Tamil Nadu
        self.category_hierarchy = {
            'OC': 0,
            'BC': 1,
            'BCM': 1,
            'MBC': 2,
            'DNC': 2,
            'SC': 3,
            'SCA': 3,
            'ST': 4
        }
        
        # Branch popularity weights (higher = more popular)
        self.branch_popularity = {
            'CS': 10, 'AI': 10, 'DS': 9,
            'IT': 8, 'EC': 7, 'EE': 6,
            'ME': 5, 'CE': 4, 'CH': 3,
            'BT': 3, 'AE': 3, 'MT': 2
        }
    
    def load_cleaned_data(self) -> Dict[str, pd.DataFrame]:
        """Load all cleaned datasets."""
        datasets = {}
        
        files = {
            'college': 'college_cleaned.csv',
            'cutoff': 'cutoff_cleaned.csv',
            'student': 'student_cleaned.csv',
            'district': 'district_cleaned.csv',
            'scholarship': 'scholarship_cleaned.csv'
        }
        
        for name, filename in files.items():
            filepath = self.cleaned_data_path / filename
            if filepath.exists():
                datasets[name] = pd.read_csv(filepath)
                print(f"Loaded: {filename}")
            else:
                print(f"Warning: {filename} not found")
        
        return datasets
    
    def create_college_features(self, college_df: pd.DataFrame, cutoff_df: pd.DataFrame) -> pd.DataFrame:
        """Create enhanced features for colleges."""
        # Aggregate cutoff statistics per college
        cutoff_stats = cutoff_df.groupby('college_id').agg({
            'cutoff_2023': ['mean', 'min', 'max'],
            'seats_available': 'sum',
            'branch_code': 'nunique',
            'cutoff_trend': 'mean'
        }).reset_index()
        
        # Flatten column names
        cutoff_stats.columns = [
            'college_id', 'avg_cutoff', 'min_cutoff', 'max_cutoff',
            'total_seats', 'num_branches', 'avg_cutoff_trend'
        ]
        
        # Merge with college data
        enhanced_df = college_df.merge(cutoff_stats, on='college_id', how='left')
        
        # Create features
        enhanced_df['selectivity_score'] = (enhanced_df['avg_cutoff'] / 200 * 100).round(2)
        
        # College type encoding
        type_scores = {'Government': 3, 'Private Aided': 2, 'Private': 1}
        enhanced_df['college_type_score'] = enhanced_df['college_type'].map(type_scores).fillna(1)
        
        # Accreditation score
        accred_scores = {'Naac A++': 5, 'Naac A+': 4, 'Naac A': 3, 'Naac B++': 2, 'Naac B+': 1}
        enhanced_df['accreditation_score'] = enhanced_df['accreditation'].map(accred_scores).fillna(1)
        
        # Overall college score (weighted combination)
        enhanced_df['overall_score'] = (
            enhanced_df['quality_score'] * 0.3 +
            enhanced_df['placement_rate'] * 0.25 +
            enhanced_df['accreditation_score'] * 10 +
            enhanced_df['college_type_score'] * 10 +
            (100 - enhanced_df['ranking']) * 0.15
        ).round(2)
        
        # Hostel availability binary
        enhanced_df['has_hostel'] = enhanced_df['hostel_available'].apply(
            lambda x: 1 if str(x).lower() == 'yes' else 0
        )
        
        return enhanced_df
    
    def create_student_features(self, student_df: pd.DataFrame) -> pd.DataFrame:
        """Create enhanced features for students."""
        enhanced_df = student_df.copy()
        
        # Academic performance tier
        enhanced_df['performance_tier'] = pd.cut(
            enhanced_df['cutoff_score'],
            bins=[0, 150, 170, 185, 195, 200],
            labels=['Tier5', 'Tier4', 'Tier3', 'Tier2', 'Tier1']
        )
        
        # Category priority score
        enhanced_df['category_priority'] = enhanced_df['category'].map(self.category_hierarchy).fillna(0)
        
        # Income bracket
        enhanced_df['income_bracket'] = pd.cut(
            enhanced_df['annual_income'],
            bins=[0, 200000, 400000, 600000, 1000000, float('inf')],
            labels=['Very Low', 'Low', 'Medium', 'High', 'Very High']
        )
        
        # Subject strength analysis
        enhanced_df['math_strength'] = enhanced_df['maths_marks'] / enhanced_df[['physics_marks', 'chemistry_marks', 'maths_marks']].max(axis=1)
        enhanced_df['physics_strength'] = enhanced_df['physics_marks'] / enhanced_df[['physics_marks', 'chemistry_marks', 'maths_marks']].max(axis=1)
        
        # Recommend branch based on strengths
        def recommend_branch_type(row):
            if row['maths_marks'] > row['physics_marks'] and row['maths_marks'] > row['chemistry_marks']:
                return 'CS/IT/AI'
            elif row['physics_marks'] > row['chemistry_marks']:
                return 'EC/EE/ME'
            else:
                return 'CH/BT/CE'
        
        enhanced_df['recommended_branch_type'] = enhanced_df.apply(recommend_branch_type, axis=1)
        
        # Scholarship eligibility score
        enhanced_df['scholarship_potential'] = (
            (enhanced_df['category_priority'] * 10) +
            (enhanced_df['annual_income'] < 400000).astype(int) * 20 +
            (enhanced_df['cutoff_score'] > 180).astype(int) * 15 +
            (enhanced_df['gender'] == 'Female').astype(int) * 10
        )
        
        return enhanced_df
    
    def create_district_features(self, district_df: pd.DataFrame) -> pd.DataFrame:
        """Create enhanced features for districts."""
        enhanced_df = district_df.copy()
        
        # Normalize ratings to 0-100 scale
        scaler = MinMaxScaler(feature_range=(0, 100))
        
        # Overall district score
        enhanced_df['accessibility_score'] = (
            (enhanced_df['transport_connectivity'].map({
                'Excellent': 100, 'Good': 75, 'Moderate': 50, 'Poor': 25
            }).fillna(50))
        )
        
        # Cost efficiency score (lower cost = higher score)
        max_cost = enhanced_df['avg_living_cost_monthly'].max()
        enhanced_df['cost_efficiency_score'] = (
            (1 - enhanced_df['avg_living_cost_monthly'] / max_cost) * 100
        ).round(2)
        
        # Education hub score
        enhanced_df['education_hub_score'] = (
            enhanced_df['num_engineering_colleges'] * 3 +
            enhanced_df['num_govt_colleges'] * 5 +
            enhanced_df['student_friendly_rating'] * 15
        ).round(2)
        
        # Overall livability score
        enhanced_df['livability_score'] = (
            enhanced_df['education_index'] * 0.3 +
            enhanced_df['accessibility_score'] * 0.25 +
            enhanced_df['cost_efficiency_score'] * 0.25 +
            enhanced_df['student_friendly_rating'] * 4
        ).round(2)
        
        # Distance category
        enhanced_df['distance_category'] = pd.cut(
            enhanced_df['distance_to_chennai_km'],
            bins=[0, 100, 300, 500, float('inf')],
            labels=['Near', 'Moderate', 'Far', 'Very Far']
        )
        
        return enhanced_df
    
    def create_scholarship_features(self, scholarship_df: pd.DataFrame) -> pd.DataFrame:
        """Create enhanced features for scholarships."""
        enhanced_df = scholarship_df.copy()
        
        # Value score (amount relative to max)
        max_value = enhanced_df['total_value'].max()
        enhanced_df['value_score'] = (enhanced_df['total_value'] / max_value * 100).round(2)
        
        # Accessibility score (based on eligibility criteria strictness)
        enhanced_df['accessibility_score'] = 100
        
        # Reduce score based on restrictions
        enhanced_df.loc[enhanced_df['income_limit'] > 0, 'accessibility_score'] -= 20
        enhanced_df.loc[enhanced_df['min_cutoff'] > 0, 'accessibility_score'] -= 20
        enhanced_df.loc[enhanced_df['min_percentage'] > 0, 'accessibility_score'] -= 15
        enhanced_df.loc[enhanced_df['gender'] != 'All', 'accessibility_score'] -= 15
        enhanced_df.loc[enhanced_df['category_eligible'] != 'ALL', 'accessibility_score'] -= 15
        
        # Provider reliability score
        provider_scores = {
            'Government Of Tamil Nadu': 95,
            'Government Of India': 98,
            'Aicte': 90,
            'Private': 75,
            'State Government': 85
        }
        enhanced_df['provider_reliability'] = enhanced_df['provider'].map(provider_scores).fillna(70)
        
        # Overall scholarship attractiveness
        enhanced_df['attractiveness_score'] = (
            enhanced_df['value_score'] * 0.4 +
            enhanced_df['accessibility_score'] * 0.3 +
            enhanced_df['provider_reliability'] * 0.3
        ).round(2)
        
        return enhanced_df
    
    def create_cutoff_features(self, cutoff_df: pd.DataFrame) -> pd.DataFrame:
        """Create enhanced features for cutoffs."""
        enhanced_df = cutoff_df.copy()
        
        # Branch popularity score
        enhanced_df['branch_popularity'] = enhanced_df['branch_code'].map(self.branch_popularity).fillna(3)
        
        # Cutoff stability (lower variance = more stable)
        cutoff_cols = ['cutoff_2023', 'cutoff_2022', 'cutoff_2021']
        enhanced_df['cutoff_variance'] = enhanced_df[cutoff_cols].var(axis=1).round(2)
        enhanced_df['cutoff_stability'] = (100 - enhanced_df['cutoff_variance']).clip(0, 100).round(2)
        
        # Seat availability category
        enhanced_df['seat_category'] = pd.cut(
            enhanced_df['seats_available'],
            bins=[0, 30, 60, 100, float('inf')],
            labels=['Limited', 'Moderate', 'Good', 'Excellent']
        )
        
        # Competition intensity (higher cutoff + fewer seats = more competitive)
        max_cutoff = enhanced_df['cutoff_2023'].max()
        max_seats = enhanced_df['seats_available'].max()
        enhanced_df['competition_intensity'] = (
            (enhanced_df['cutoff_2023'] / max_cutoff * 50) +
            ((1 - enhanced_df['seats_available'] / max_seats) * 50)
        ).round(2)
        
        # Category advantage score
        category_advantage = {'OC': 0, 'BC': 15, 'MBC': 25, 'SC': 35, 'ST': 40}
        enhanced_df['category_advantage'] = enhanced_df['category'].map(category_advantage).fillna(0)
        
        return enhanced_df
    
    def process_all_data(self) -> Dict[str, pd.DataFrame]:
        """Process all datasets and save to processed directory."""
        # Load cleaned data
        datasets = self.load_cleaned_data()
        
        if not datasets:
            print("No datasets found to process!")
            return {}
        
        processed = {}
        
        # Process each dataset
        print("\nProcessing College features...")
        if 'college' in datasets and 'cutoff' in datasets:
            processed['college'] = self.create_college_features(datasets['college'], datasets['cutoff'])
        
        print("Processing Student features...")
        if 'student' in datasets:
            processed['student'] = self.create_student_features(datasets['student'])
        
        print("Processing District features...")
        if 'district' in datasets:
            processed['district'] = self.create_district_features(datasets['district'])
        
        print("Processing Scholarship features...")
        if 'scholarship' in datasets:
            processed['scholarship'] = self.create_scholarship_features(datasets['scholarship'])
        
        print("Processing Cutoff features...")
        if 'cutoff' in datasets:
            processed['cutoff'] = self.create_cutoff_features(datasets['cutoff'])
        
        # Save processed datasets
        for name, df in processed.items():
            output_path = self.processed_data_path / f"{name}_processed.csv"
            df.to_csv(output_path, index=False)
            print(f"Saved: {output_path} ({len(df)} records, {len(df.columns)} features)")
        
        return processed
    
    def get_feature_summary(self, df: pd.DataFrame) -> Dict:
        """Get summary of features in a dataframe."""
        return {
            'total_features': len(df.columns),
            'numeric_features': len(df.select_dtypes(include=[np.number]).columns),
            'categorical_features': len(df.select_dtypes(include=['object']).columns),
            'feature_list': list(df.columns),
            'sample_record': df.iloc[0].to_dict() if len(df) > 0 else {}
        }


if __name__ == "__main__":
    # Test the preprocessor
    preprocessor = DataPreprocessor()
    processed_data = preprocessor.process_all_data()
    
    # Show feature summaries
    for name, df in processed_data.items():
        summary = preprocessor.get_feature_summary(df)
        print(f"\n=== {name.upper()} Features ===")
        print(f"Total: {summary['total_features']}")
        print(f"Numeric: {summary['numeric_features']}")
        print(f"Categorical: {summary['categorical_features']}")










