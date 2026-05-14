"""
Models for Scholarship data.
"""

from django.db import models
from django.conf import settings


class Scholarship(models.Model):
    """Scholarship model."""
    
    GENDER_CHOICES = [
        ('All', 'All'),
        ('Male', 'Male Only'),
        ('Female', 'Female Only'),
    ]
    
    AMOUNT_CATEGORY_CHOICES = [
        ('Basic', 'Basic (< ₹15,000)'),
        ('Standard', 'Standard (₹15,000 - ₹30,000)'),
        ('Premium', 'Premium (₹30,000 - ₹50,000)'),
        ('Elite', 'Elite (> ₹50,000)'),
    ]
    
    scholarship_id = models.CharField(max_length=20, unique=True, primary_key=True)
    scholarship_name = models.CharField(max_length=200)
    provider = models.CharField(max_length=100)
    
    # Eligibility criteria
    category_eligible = models.CharField(max_length=50, default='All')
    income_limit = models.IntegerField(default=0, help_text='0 means no limit')
    min_cutoff = models.FloatField(default=0)
    min_percentage = models.FloatField(default=0)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='All')
    
    # Benefits
    amount_per_year = models.IntegerField()
    duration_years = models.IntegerField(default=4)
    total_value = models.IntegerField(default=0)
    amount_category = models.CharField(max_length=20, choices=AMOUNT_CATEGORY_CHOICES, default='Standard')
    
    # Additional info
    application_deadline = models.DateField(null=True, blank=True)
    documents_required = models.TextField(blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    
    # Computed scores
    accessibility_score = models.FloatField(default=50)
    provider_reliability = models.FloatField(default=70)
    attractiveness_score = models.FloatField(default=50)
    
    class Meta:
        ordering = ['-amount_per_year']
        verbose_name = 'Scholarship'
        verbose_name_plural = 'Scholarships'
    
    def __str__(self):
        return f"{self.scholarship_name} (₹{self.amount_per_year}/year)"
    
    def save(self, *args, **kwargs):
        # Calculate total value
        self.total_value = self.amount_per_year * self.duration_years
        
        # Set amount category
        if self.amount_per_year < 15000:
            self.amount_category = 'Basic'
        elif self.amount_per_year < 30000:
            self.amount_category = 'Standard'
        elif self.amount_per_year < 50000:
            self.amount_category = 'Premium'
        else:
            self.amount_category = 'Elite'
        
        super().save(*args, **kwargs)
    
    def get_eligible_categories(self):
        """Parse eligible categories."""
        if self.category_eligible.upper() == 'ALL':
            return ['ALL']
        return [c.strip() for c in self.category_eligible.split('/')]


class ScholarshipApplication(models.Model):
    """Track scholarship applications."""
    
    STATUS_CHOICES = [
        ('interested', 'Interested'),
        ('applied', 'Applied'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scholarship_applications')
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name='applications')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='interested')
    eligibility_status = models.CharField(max_length=20, default='unknown')
    match_score = models.FloatField(default=0)
    
    notes = models.TextField(blank=True)
    applied_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'scholarship']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.scholarship.scholarship_name} ({self.status})"










