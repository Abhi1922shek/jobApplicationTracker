from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.conf import settings # Used for settings.AUTH_USER_MODEL
from .utils import get_jd_resume_match_score # For resume scoring

# --- Custom User Model and Manager ---
class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None # Remove username field
    email = models.EmailField('email address', unique=True) # Email as the unique identifier

    USERNAME_FIELD = 'email' # Use email for login
    REQUIRED_FIELDS = [] # No other fields required for createsuperuser besides email and password

    objects = CustomUserManager() # Assign the custom manager

    def __str__(self):
        return self.email


# --- Company Model ---
class Company(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Use the custom user model defined in settings
        on_delete=models.CASCADE,
        help_text="The user who owns this company entry."
    )
    name = models.CharField(max_length=200, help_text="Name of the company.")
    website = models.URLField(blank=True, null=True, help_text="Company's website (optional).")

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


# --- JobApplication Model ---
class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('APPLIED', 'Applied'),
        ('ASSESSMENT', 'Online Assessment'),
        ('INTERVIEW_R1', 'Interview Round 1'),
        ('INTERVIEW_R2', 'Interview Round 2'),
        ('INTERVIEW_R3_PLUS', 'Interview Round 3+'),
        ('OFFER_RECEIVED', 'Offer Received'),
        ('OFFER_ACCEPTED', 'Offer Accepted'),
        ('OFFER_DECLINED', 'Offer Declined'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),
        ('GHOSTED', 'Ghosted / No Response'),
    ]

    APPLICATION_SOURCE_CHOICES = [
        ('LINKEDIN', 'LinkedIn'),
        ('INDEED', 'Indeed'),
        ('COMPANY_WEBSITE', 'Company Website'),
        ('JOB_BOARD_OTHER', 'Other Job Board (e.g., Glassdoor, Monster)'),
        ('REFERRAL', 'Referral'),
        ('NETWORKING', 'Networking Event / Contact'),
        ('CAREER_FAIR', 'Career Fair'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Use the custom user model
        on_delete=models.CASCADE,
        help_text="The user who owns this application entry."
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select a company from your list. If the company is new, add it first or use 'Company Name (Manual)'. "
    )
    company_name_manual = models.CharField(
        max_length=200,
        blank=True,
        help_text="Use this if you don't want to add the company to your main list, or for a one-off application."
    )
    job_title = models.CharField(max_length=200, help_text="The title of the job you applied for.")
    job_description = models.TextField(blank=True, help_text="Copy-paste the Job Description here (optional).")
    application_link = models.URLField(blank=True, null=True, help_text="Link to the job posting or application portal (optional).")

    application_source = models.CharField(
        max_length=50,
        choices=APPLICATION_SOURCE_CHOICES,
        blank=True,
        null=True,
        default=None,
        help_text="Where did you find/apply for this job?"
    )

    applied_date = models.DateField(default=timezone.now, help_text="The date you submitted the application.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='APPLIED', help_text="Current status of your application.")
    resume_submitted = models.FileField(upload_to='resumes/%Y/%m/%d/', blank=True, null=True, help_text="The resume PDF/DOCX you submitted (optional).")
    notes = models.TextField(blank=True, help_text="Any personal notes, contacts, or next steps (optional).")
    last_reminder_sent_date = models.DateField(blank=True, null=True, editable=False, help_text="Internal field: Date last reminder email was sent.")
    resume_match_score = models.FloatField(blank=True, null=True, editable=False, help_text="Internal field: Calculated match score between resume and JD.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_company_name(self):
        if self.company:
            return self.company.name
        return self.company_name_manual or "N/A"

    def __str__(self):
        # Using user.email because your CustomUser __str__ returns email
        return f"{self.job_title} at {self.get_company_name()} (User: {self.user.email})"

    def save(self, *args, **kwargs):
        # --- THIS IS THE ADDED/UPDATED save() METHOD FOR SCORING ---
        recalculate_score = False
        is_new = self.pk is None

        if not is_new:
            try:
                old_instance = JobApplication.objects.get(pk=self.pk)
                if (old_instance.job_description != self.job_description or
                    (self.resume_submitted and old_instance.resume_submitted != self.resume_submitted) or
                    (self.resume_submitted and not old_instance.resume_submitted)):
                    recalculate_score = True
            except JobApplication.DoesNotExist:
                recalculate_score = True
        elif self.job_description and self.resume_submitted:
            recalculate_score = True

        super().save(*args, **kwargs) # Call original save method first

        if recalculate_score and self.job_description and self.resume_submitted and hasattr(self.resume_submitted, 'path'):
            try:
                print(f"Recalculating match score for application ID: {self.id}")
                resume_path = self.resume_submitted.path
                score = get_jd_resume_match_score(self.job_description, resume_path)
                
                self.__class__.objects.filter(pk=self.pk).update(resume_match_score=score)
                self.resume_match_score = score # Update current instance
                print(f"Score {score:.2f}% saved for application ID: {self.id}")
            except Exception as e:
                print(f"Error calculating or saving resume match score for application ID {self.id}: {e}")
                self.__class__.objects.filter(pk=self.pk).update(resume_match_score=None)
                self.resume_match_score = None
        elif recalculate_score:
            missing_parts = []
            if not self.job_description: missing_parts.append("job description")
            if not self.resume_submitted: missing_parts.append("resume")
            elif not hasattr(self.resume_submitted, 'path'): missing_parts.append("valid resume path")
            if missing_parts:
                print(f"Skipping score calculation for application ID {self.id}: Missing {', '.join(missing_parts)}.")
        # --- END OF save() METHOD FOR SCORING ---

    class Meta:
        ordering = ['-applied_date', '-updated_at']
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"