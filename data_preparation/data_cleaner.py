"""
Data Cleaner Module
Handles cleaning and validation of raw datasets
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


class DataCleaner:
    """
    Cleans and validates raw dataset files for the college recommendation system.
    """
    
    def __init__(self, raw_data_path: str = "datasets/raw", clean_data_path: str = "datasets/cleaned"):
        self.raw_data_path = Path(raw_data_path)
        self.clean_data_path = Path(clean_data_path)
        self.clean_data_path.mkdir(parents=True, exist_ok=True)
        
        # Data validation rules
        self.validation_rules = {
            'college': {
                'required_columns': ['college_id', 'college_name', 'college_type', 'district'],
                'numeric_columns': ['established_year', 'ranking', 'total_seats', 'placement_rate', 'avg_package_lpa'],
                'categorical_columns': ['college_type', 'accreditation', 'hostel_available']
            },
            'cutoff': {
                'required_columns': ['cutoff_id', 'college_id', 'branch_code', 'branch_name', 'category'],
                'numeric_columns': ['cutoff_2023', 'cutoff_2022', 'cutoff_2021', 'seats_available', 'min_cutoff', 'max_cutoff'],
                'categorical_columns': ['category']
            },
            'student': {
                'required_columns': ['student_id', 'name', 'email', 'category', 'district'],
                'numeric_columns': ['physics_marks', 'chemistry_marks', 'maths_marks', 'cutoff_score', 'annual_income'],
                'categorical_columns': ['gender', 'category', 'board', 'hostel_required']
            },
            'district': {
                'required_columns': ['district_id', 'district_name', 'zone'],
                'numeric_columns': ['population', 'literacy_rate', 'num_engineering_colleges', 'avg_living_cost_monthly', 'distance_to_chennai_km', 'student_friendly_rating'],
                'categorical_columns': ['zone', 'transport_connectivity']
            },
            'scholarship': {
                'required_columns': ['scholarship_id', 'scholarship_name', 'provider', 'category_eligible'],
                'numeric_columns': ['income_limit', 'min_cutoff', 'min_percentage', 'amount_per_year', 'duration_years'],
                'categorical_columns': ['category_eligible', 'gender']
            }
        }
    
    def clean_college_data(self, filename: str = "College_TN.csv") -> pd.DataFrame:
        """Clean and validate college dataset."""
        df = pd.read_csv(self.raw_data_path / filename)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['college_id'])
        
        # Clean string columns
        string_cols = ['college_name', 'college_type', 'district', 'city', 'accreditation']
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].str.strip().str.title()
        
        # Standardize college types
        df['college_type'] = df['college_type'].replace({
            'Govt': 'Government',
            'Pvt': 'Private',
            'Private Aided': 'Private Aided'
        })
        
        # Handle missing values
        df['hostel_available'] = df['hostel_available'].fillna('Unknown')
        df['placement_rate'] = df['placement_rate'].fillna(df['placement_rate'].median())
        df['avg_package_lpa'] = df['avg_package_lpa'].fillna(df['avg_package_lpa'].median())
        
        # Validate numeric ranges
        df['placement_rate'] = df['placement_rate'].clip(0, 100)
        df['ranking'] = df['ranking'].clip(1, 1000)
        
        # Add computed columns
        df['quality_score'] = (
            df['placement_rate'] * 0.4 +
            df['avg_package_lpa'] * 5 +
            (100 - df['ranking']) * 0.3
        ).round(2)
        
        return df
    
    def clean_cutoff_data(self, filename: str = "College_branch_cutoffs.csv") -> pd.DataFrame:
        """Clean and validate cutoff dataset."""
        df = pd.read_csv(self.raw_data_path / filename)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['cutoff_id'])
        
        # Clean string columns
        df['branch_name'] = df['branch_name'].str.strip().str.title()
        df['branch_code'] = df['branch_code'].str.strip().str.upper()
        df['category'] = df['category'].str.strip().str.upper()
        
        # Standardize category names
        category_mapping = {
            'OC': 'OC',
            'BC': 'BC',
            'BCM': 'BC',
            'MBC': 'MBC',
            'SC': 'SC',
            'ST': 'ST',
            'SCA': 'SC'
        }
        df['category'] = df['category'].replace(category_mapping)
        
        # Handle missing cutoffs (use average of available years)
        cutoff_cols = ['cutoff_2023', 'cutoff_2022', 'cutoff_2021']
        for col in cutoff_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['avg_cutoff'] = df[cutoff_cols].mean(axis=1).round(2)
        
        # Fill missing cutoffs with average
        for col in cutoff_cols:
            df[col] = df[col].fillna(df['avg_cutoff'])
        
        # Validate cutoff ranges (0-200 for TN engineering)
        for col in cutoff_cols + ['min_cutoff', 'max_cutoff']:
            df[col] = df[col].clip(0, 200)
        
        # Calculate cutoff trend
        df['cutoff_trend'] = ((df['cutoff_2023'] - df['cutoff_2021']) / 2).round(2)
        
        return df
    
    def clean_student_data(self, filename: str = "Student.csv") -> pd.DataFrame:
        """Clean and validate student dataset."""
        df = pd.read_csv(self.raw_data_path / filename)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['student_id'])
        
        # Clean string columns
        df['name'] = df['name'].str.strip().str.title()
        df['email'] = df['email'].str.strip().str.lower()
        df['district'] = df['district'].str.strip().str.title()
        df['category'] = df['category'].str.strip().str.upper()
        df['gender'] = df['gender'].str.strip().str.title()
        
        # Validate email format
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        df['email_valid'] = df['email'].apply(lambda x: bool(re.match(email_pattern, str(x))))
        
        # Validate marks (0-100)
        marks_cols = ['physics_marks', 'chemistry_marks', 'maths_marks']
        for col in marks_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').clip(0, 100)
        
        # Recalculate cutoff score (TN formula: Maths + Physics/2 + Chemistry/2)
        df['calculated_cutoff'] = (
            df['maths_marks'] + 
            df['physics_marks'] / 2 + 
            df['chemistry_marks'] / 2
        ).round(2)
        
        # Use calculated cutoff if original is missing or invalid
        df['cutoff_score'] = df.apply(
            lambda row: row['calculated_cutoff'] if pd.isna(row['cutoff_score']) or row['cutoff_score'] > 200 
            else row['cutoff_score'],
            axis=1
        )
        
        # Standardize hostel requirement
        df['hostel_required'] = df['hostel_required'].replace({
            'Yes': True, 'yes': True, 'YES': True, 'Y': True,
            'No': False, 'no': False, 'NO': False, 'N': False
        })
        
        # Calculate total percentage
        df['total_percentage'] = ((df['physics_marks'] + df['chemistry_marks'] + df['maths_marks']) / 3).round(2)
        
        return df
    
    def clean_district_data(self, filename: str = "District_TN.csv") -> pd.DataFrame:
        """Clean and validate district dataset."""
        df = pd.read_csv(self.raw_data_path / filename)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['district_id'])
        
        # Clean string columns
        df['district_name'] = df['district_name'].str.strip().str.title()
        df['zone'] = df['zone'].str.strip().str.title()
        df['transport_connectivity'] = df['transport_connectivity'].str.strip().str.title()
        
        # Handle missing values
        df['literacy_rate'] = df['literacy_rate'].fillna(df['literacy_rate'].median())
        df['student_friendly_rating'] = df['student_friendly_rating'].fillna(3.0)
        
        # Validate ranges
        df['literacy_rate'] = df['literacy_rate'].clip(0, 100)
        df['student_friendly_rating'] = df['student_friendly_rating'].clip(1, 5)
        
        # Calculate education index
        df['education_index'] = (
            df['literacy_rate'] * 0.3 +
            df['num_engineering_colleges'] * 2 +
            df['student_friendly_rating'] * 10
        ).round(2)
        
        # Categorize living cost
        df['cost_category'] = pd.cut(
            df['avg_living_cost_monthly'],
            bins=[0, 12000, 16000, 20000, float('inf')],
            labels=['Low', 'Medium', 'High', 'Very High']
        )
        
        return df
    
    def clean_scholarship_data(self, filename: str = "Scholarship_TN.csv") -> pd.DataFrame:
        """Clean and validate scholarship dataset."""
        df = pd.read_csv(self.raw_data_path / filename)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['scholarship_id'])
        
        # Clean string columns
        df['scholarship_name'] = df['scholarship_name'].str.strip()
        df['provider'] = df['provider'].str.strip().str.title()
        df['category_eligible'] = df['category_eligible'].str.strip().str.upper()
        df['gender'] = df['gender'].str.strip().str.title()
        
        # Handle missing values
        df['income_limit'] = df['income_limit'].fillna(0)  # 0 means no limit
        df['min_cutoff'] = df['min_cutoff'].fillna(0)
        df['min_percentage'] = df['min_percentage'].fillna(0)
        
        # Parse category eligibility into list
        df['eligible_categories'] = df['category_eligible'].apply(
            lambda x: [c.strip() for c in str(x).split('/')] if pd.notna(x) else ['ALL']
        )
        
        # Calculate total scholarship value
        df['total_value'] = df['amount_per_year'] * df['duration_years']
        
        # Categorize scholarship by amount
        df['amount_category'] = pd.cut(
            df['amount_per_year'],
            bins=[0, 15000, 30000, 50000, float('inf')],
            labels=['Basic', 'Standard', 'Premium', 'Elite']
        )
        
        return df
    
    def clean_all_datasets(self) -> Dict[str, pd.DataFrame]:
        """Clean all datasets and save to cleaned directory."""
        cleaned_datasets = {}
        
        # Clean each dataset
        print("Cleaning College data...")
        cleaned_datasets['college'] = self.clean_college_data()
        
        print("Cleaning Cutoff data...")
        cleaned_datasets['cutoff'] = self.clean_cutoff_data()
        
        print("Cleaning Student data...")
        cleaned_datasets['student'] = self.clean_student_data()
        
        print("Cleaning District data...")
        cleaned_datasets['district'] = self.clean_district_data()
        
        print("Cleaning Scholarship data...")
        cleaned_datasets['scholarship'] = self.clean_scholarship_data()
        
        # Save cleaned datasets
        for name, df in cleaned_datasets.items():
            output_path = self.clean_data_path / f"{name}_cleaned.csv"
            df.to_csv(output_path, index=False)
            print(f"Saved: {output_path} ({len(df)} records)")
        
        return cleaned_datasets
    
    def validate_dataset(self, df: pd.DataFrame, dataset_type: str) -> Tuple[bool, List[str]]:
        """Validate a dataset against defined rules."""
        errors = []
        rules = self.validation_rules.get(dataset_type, {})
        
        # Check required columns
        required_cols = rules.get('required_columns', [])
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
        
        # Check for null values in required columns
        for col in required_cols:
            if col in df.columns and df[col].isnull().any():
                null_count = df[col].isnull().sum()
                errors.append(f"Column '{col}' has {null_count} null values")
        
        # Check numeric columns
        numeric_cols = rules.get('numeric_columns', [])
        for col in numeric_cols:
            if col in df.columns:
                non_numeric = df[col].apply(lambda x: not isinstance(x, (int, float)) and pd.notna(x)).sum()
                if non_numeric > 0:
                    errors.append(f"Column '{col}' has {non_numeric} non-numeric values")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def get_data_quality_report(self, df: pd.DataFrame, name: str) -> Dict:
        """Generate a data quality report for a dataset."""
        # Calculate duplicates only on hashable columns
        try:
            # Filter out columns with unhashable types (like lists)
            hashable_cols = []
            for col in df.columns:
                try:
                    # Test if column values are hashable
                    df[col].apply(hash)
                    hashable_cols.append(col)
                except TypeError:
                    continue
            
            if hashable_cols:
                duplicate_count = int(df[hashable_cols].duplicated().sum())
            else:
                duplicate_count = 0
        except Exception:
            duplicate_count = 0
        
        report = {
            'dataset_name': name,
            'total_records': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicate_count': duplicate_count,
            'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024),
            'numeric_stats': {},
            'categorical_stats': {}
        }
        
        # Numeric column statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            report['numeric_stats'][col] = {
                'min': float(df[col].min()) if pd.notna(df[col].min()) else None,
                'max': float(df[col].max()) if pd.notna(df[col].max()) else None,
                'mean': float(df[col].mean()) if pd.notna(df[col].mean()) else None,
                'median': float(df[col].median()) if pd.notna(df[col].median()) else None
            }
        
        # Categorical column statistics (only for hashable columns)
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            try:
                report['categorical_stats'][col] = {
                    'unique_values': int(df[col].nunique()),
                    'top_values': df[col].value_counts().head(5).to_dict()
                }
            except TypeError:
                # Skip columns with unhashable types
                report['categorical_stats'][col] = {
                    'unique_values': 'N/A (contains lists)',
                    'top_values': {}
                }
        
        return report


if __name__ == "__main__":
    # Test the cleaner
    cleaner = DataCleaner()
    datasets = cleaner.clean_all_datasets()
    
    # Generate quality reports
    for name, df in datasets.items():
        report = cleaner.get_data_quality_report(df, name)
        print(f"\n=== {name.upper()} Dataset Report ===")
        print(f"Records: {report['total_records']}")
        print(f"Columns: {report['total_columns']}")
        print(f"Duplicates: {report['duplicate_count']}")


