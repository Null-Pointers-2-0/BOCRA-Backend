"""
Custom User model with role-based access control.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel
from apps.core.managers import ActiveManager, AllObjectsManager
from apps.accounts.managers import UserManager
from apps.core.utils import validate_botswana_phone_number, validate_botswana_id_number


class User(AbstractUser, BaseModel):
    """
    Custom User model extending Django's AbstractUser.
    
    Adds:
    - Role field for RBAC (Role-Based Access Control)
    - Email verification status
    - Phone number for Botswana users
    - ID number for Botswana citizens
    
    Roles:
    - CITIZEN: Regular users who apply for licences and file complaints
    - STAFF: BOCRA staff who process applications and complaints
    - ADMIN: System administrators with full access
    
    Security Features:
    - Email-based authentication (more secure than username)
    - Phone number validation for Botswana format
    - ID number validation for Botswana citizens
    - Soft delete capability through BaseModel
    """
    
    class Role(models.TextChoices):
        """User roles with clear hierarchy and permissions."""
        CITIZEN = 'CITIZEN', 'Citizen'
        STAFF = 'STAFF', 'BOCRA Staff'
        ADMIN = 'ADMIN', 'Administrator'
    
    # Role-based access control
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CITIZEN,
        help_text="User's role determines their access permissions"
    )
    
    # Email as primary identifier
    email = models.EmailField(
        unique=True,
        help_text="Primary email address for notifications"
    )
    email_verified = models.BooleanField(
        default=False,
        help_text="Whether the user has verified their email"
    )
    
    # Botswana-specific fields
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?267?\d{8}$',
                message="Phone number must be in format +267XXXXXXXX or XXXXXXXX"
            )
        ],
        help_text="Botswana phone number in format +267XXXXXXXX"
    )
    id_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Botswana National ID (Omang) or Passport number"
    )
    
    # Profile information
    first_name = models.CharField(
        max_length=150,
        help_text="First name"
    )
    last_name = models.CharField(
        max_length=150,
        help_text="Last name"
    )
    
    # Timestamps for tracking
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of last login"
    )
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of failed login attempts"
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this time after too many failed attempts"
    )
    
    # Make email the primary identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    # Custom managers
    objects = UserManager()
    all_objects = AllObjectsManager()
    
    class Meta:
        db_table = 'accounts_user'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['email_verified']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    
    def __str__(self):
        """String representation showing email and role."""
        return f"{self.email} ({self.get_role_display()})"
    
    def clean(self):
        """
        Validate model fields before saving.
        
        Raises:
            ValidationError: If validation fails
        """
        super().clean()
        
        # Validate phone number format
        if self.phone_number and not validate_botswana_phone_number(self.phone_number):
            raise ValidationError({
                'phone_number': 'Invalid Botswana phone number format'
            })
        
        # Validate ID number format
        if self.id_number and not validate_botswana_id_number(self.id_number):
            raise ValidationError({
                'id_number': 'Invalid Botswana ID number format'
            })
    
    @property
    def full_name(self):
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_staff_member(self):
        """
        Check if user has staff or admin role.
        
        Returns:
            bool: True if user is staff or admin
        """
        return self.role in [self.Role.STAFF, self.Role.ADMIN]
    
    @property
    def is_admin(self):
        """
        Check if user has admin role.
        
        Returns:
            bool: True if user is admin
        """
        return self.role == self.Role.ADMIN
    
    @property
    def is_citizen(self):
        """
        Check if user has citizen role.
        
        Returns:
            bool: True if user is citizen
        """
        return self.role == self.Role.CITIZEN
    
    @property
    def is_locked(self):
        """
        Check if user account is temporarily locked.
        
        Returns:
            bool: True if account is locked
        """
        if not self.locked_until:
            return False
        
        from django.utils import timezone
        return timezone.now() < self.locked_until
    
    def verify_email(self):
        """Mark the user's email as verified."""
        self.email_verified = True
        self.save(update_fields=['email_verified'])
    
    def lock_account(self, hours=24):
        """
        Lock user account for specified hours.
        
        Args:
            hours (int): Number of hours to lock the account
        """
        from django.utils import timezone
        from datetime import timedelta
        
        self.locked_until = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['locked_until'])
    
    def unlock_account(self):
        """Unlock user account."""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts'])
    
    def increment_failed_login(self):
        """Increment failed login attempts."""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account()
        
        self.save(update_fields=['failed_login_attempts', 'locked_until'])
    
    def reset_failed_login(self):
        """Reset failed login attempts."""
        self.failed_login_attempts = 0
        self.save(update_fields=['failed_login_attempts'])
    
    def can_view_licences(self):
        """
        Check if user can view licence applications.
        
        Returns:
            bool: True if user can view licences
        """
        return self.is_staff_member or self.is_citizen
    
    def can_process_licences(self):
        """
        Check if user can process licence applications.
        
        Returns:
            bool: True if user can process licences
        """
        return self.is_staff_member
    
    def can_manage_users(self):
        """
        Check if user can manage other users.
        
        Returns:
            bool: True if user can manage users
        """
        return self.is_admin
    
    def get_accessible_licences(self):
        """
        Get licence applications this user can access.
        
        Returns:
            QuerySet: Licence applications accessible to this user
        """
        from apps.licensing.models import LicenceApplication
        
        if self.is_admin:
            return LicenceApplication.objects.all()
        elif self.is_staff_member:
            return LicenceApplication.objects.all()
        else:  # Citizen
            return LicenceApplication.objects.filter(user=self)
    
    def get_accessible_complaints(self):
        """
        Get complaints this user can access.
        
        Returns:
            QuerySet: Complaints accessible to this user
        """
        from apps.complaints.models import Complaint
        
        if self.is_admin:
            return Complaint.objects.all()
        elif self.is_staff_member:
            return Complaint.objects.all()
        else:  # Citizen
            return Complaint.objects.filter(user=self)


class UserProfile(BaseModel):
    """
    Extended user profile for additional information.
    
    Stores additional user information that doesn't belong in the
    core User model, keeping it clean and focused on authentication.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Date of birth"
    )
    gender = models.CharField(
        max_length=10,
        choices=[
            ('MALE', 'Male'),
            ('FEMALE', 'Female'),
            ('OTHER', 'Other'),
        ],
        blank=True,
        help_text="Gender"
    )
    address = models.TextField(
        blank=True,
        help_text="Physical address"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text="City"
    )
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        help_text="Postal code"
    )
    # profile_picture = models.ImageField(
    #     upload_to='profile_pictures/',
    #     blank=True,
    #     null=True,
    #     help_text="Profile picture"
    # )
    bio = models.TextField(
        blank=True,
        help_text="Short biography"
    )
    website = models.URLField(
        blank=True,
        help_text="Personal website"
    )
    linkedin = models.URLField(
        blank=True,
        help_text="LinkedIn profile"
    )
    
    class Meta:
        db_table = 'accounts_user_profile'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['city']),
        ]
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def __str__(self):
        return f"{self.user.email} Profile"
    
    @property
    def age(self):
        """Calculate age from date of birth."""
        if self.date_of_birth:
            from django.utils import timezone
            today = timezone.now().date()
            age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
            return age
        return None
    
    @property
    def is_complete(self):
        """
        Check if profile is complete.
        
        Returns:
            bool: True if profile has essential information
        """
        essential_fields = [
            self.user.phone_number,
            self.user.id_number,
            self.date_of_birth,
            self.address,
            self.city
        ]
        return all(field for field in essential_fields)
