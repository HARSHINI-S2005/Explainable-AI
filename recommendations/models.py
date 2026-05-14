"""
Models for College and Recommendation data.
"""

from django.db import models
from django.conf import settings


class College(models.Model):
    """College/University model."""
    
    COLLEGE_TYPE_CHOICES = [
        ('Government', 'Government'),
        ('Private Aided', 'Private Aided'),
        ('Private', 'Private'),
    ]
    
    ACCREDITATION_CHOICES = [
        ('NAAC A++', 'NAAC A++'),
        ('NAAC A+', 'NAAC A+'),
        ('NAAC A', 'NAAC A'),
        ('NAAC B++', 'NAAC B++'),
        ('NAAC B+', 'NAAC B+'),
        ('NAAC B', 'NAAC B'),
        ('None', 'Not Accredited'),
    ]
    
    college_id = models.CharField(max_length=20, unique=True, primary_key=True)
    college_name = models.CharField(max_length=200)
    college_type = models.CharField(max_length=20, choices=COLLEGE_TYPE_CHOICES)
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    established_year = models.IntegerField(null=True, blank=True)
    accreditation = models.CharField(max_length=20, choices=ACCREDITATION_CHOICES, default='None')
    ranking = models.IntegerField(default=100)
    total_seats = models.IntegerField(default=0)
    hostel_available = models.BooleanField(default=False)
    placement_rate = models.FloatField(default=0)
    avg_package_lpa = models.FloatField(default=0)
    website = models.URLField(blank=True)
    
    # Computed scores
    quality_score = models.FloatField(default=0)
    overall_score = models.FloatField(default=0)
    
    class Meta:
        ordering = ['ranking']
        verbose_name = 'College'
        verbose_name_plural = 'Colleges'
    
    def __str__(self):
        return f"{self.college_name} ({self.college_type})"
    
    def calculate_scores(self):
        """Calculate quality and overall scores."""
        self.quality_score = round(
            self.placement_rate * 0.4 +
            self.avg_package_lpa * 5 +
            (100 - self.ranking) * 0.3,
            2
        )
        
        type_scores = {'Government': 3, 'Private Aided': 2, 'Private': 1}
        accred_scores = {'NAAC A++': 5, 'NAAC A+': 4, 'NAAC A': 3, 'NAAC B++': 2, 'NAAC B+': 1}
        
        self.overall_score = round(
            self.quality_score * 0.3 +
            self.placement_rate * 0.25 +
            accred_scores.get(self.accreditation, 1) * 10 +
            type_scores.get(self.college_type, 1) * 10 +
            (100 - self.ranking) * 0.15,
            2
        )
        return self.overall_score


class Branch(models.Model):
    """Engineering branch/department model."""
    
    branch_code = models.CharField(max_length=10, primary_key=True)
    branch_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    popularity_score = models.IntegerField(default=5)
    
    class Meta:
        ordering = ['-popularity_score']
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'
    
    def __str__(self):
        return f"{self.branch_code} - {self.branch_name}"


class CollegeBranchCutoff(models.Model):
    """Cutoff marks for college branches."""
    
    CATEGORY_CHOICES = [
        ('OC', 'OC'),
        ('BC', 'BC'),
        ('BCM', 'BCM'),
        ('MBC', 'MBC'),
        ('DNC', 'DNC'),
        ('SC', 'SC'),
        ('SCA', 'SCA'),
        ('ST', 'ST'),
    ]
    
    cutoff_id = models.CharField(max_length=20, unique=True, primary_key=True)
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='cutoffs')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='cutoffs')
    category = models.CharField(max_length=5, choices=CATEGORY_CHOICES)
    
    cutoff_2023 = models.FloatField(default=0)
    cutoff_2022 = models.FloatField(default=0)
    cutoff_2021 = models.FloatField(default=0)
    seats_available = models.IntegerField(default=0)
    min_cutoff = models.FloatField(default=0)
    max_cutoff = models.FloatField(default=200)
    
    # Computed fields
    avg_cutoff = models.FloatField(default=0)
    cutoff_trend = models.FloatField(default=0)
    competition_intensity = models.FloatField(default=50)
    
    class Meta:
        ordering = ['-cutoff_2023']
        unique_together = ['college', 'branch', 'category']
        verbose_name = 'Cutoff'
        verbose_name_plural = 'Cutoffs'
    
    def __str__(self):
        return f"{self.college.college_name} - {self.branch.branch_code} ({self.category}): {self.cutoff_2023}"
    
    def calculate_stats(self):
        """Calculate average and trend."""
        self.avg_cutoff = round(
            (self.cutoff_2023 + self.cutoff_2022 + self.cutoff_2021) / 3,
            2
        )
        self.cutoff_trend = round(
            (self.cutoff_2023 - self.cutoff_2021) / 2,
            2
        )
        
        # Competition intensity based on cutoff and seats
        max_cutoff = 200
        max_seats = 200
        self.competition_intensity = round(
            (self.cutoff_2023 / max_cutoff * 50) +
            ((1 - min(self.seats_available, max_seats) / max_seats) * 50),
            2
        )


class SavedRecommendation(models.Model):
    """Saved recommendations for a student."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_recommendations')
    college = models.ForeignKey(College, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    category = models.CharField(max_length=5)
    
    rank = models.IntegerField()
    total_score = models.FloatField()
    cutoff = models.FloatField()
    margin = models.FloatField()
    admission_probability = models.CharField(max_length=50)
    
    # Score breakdown (stored as JSON-like string or separate fields)
    score_cutoff = models.FloatField(default=0)
    score_branch = models.FloatField(default=0)
    score_quality = models.FloatField(default=0)
    score_placement = models.FloatField(default=0)
    score_location = models.FloatField(default=0)
    score_cost = models.FloatField(default=0)
    
    is_favorite = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['rank']
        unique_together = ['user', 'college', 'branch', 'category']
        verbose_name = 'Saved Recommendation'
        verbose_name_plural = 'Saved Recommendations'
    
    def __str__(self):
        return f"{self.user.username} - {self.college.college_name} ({self.branch.branch_code})"


class RecommendationHistory(models.Model):
    """History of recommendation requests."""
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendation_history')
    
    # Input parameters
    cutoff_score = models.FloatField()
    category = models.CharField(max_length=5)
    preferred_branches = models.CharField(max_length=200)  # Comma-separated
    preferred_districts = models.CharField(max_length=200)  # Comma-separated
    
    # Results summary
    total_recommendations = models.IntegerField()
    top_college = models.CharField(max_length=200)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Recommendation History'
        verbose_name_plural = 'Recommendation Histories'
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"










