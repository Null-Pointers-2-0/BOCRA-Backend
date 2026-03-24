"""
Custom user manager for the User model.
"""
from django.contrib.auth.base_user import BaseUserManager
from django.utils import timezone
from apps.core.utils import validate_botswana_phone_number, validate_botswana_id_number


class UserManager(BaseUserManager):
    """
    Custom user manager that handles user creation with email as primary identifier.
    
    Provides methods for:
    - Creating regular users
    - Creating superusers
    - Querying users by role
    - User statistics and reporting
    """
    
    def get_by_natural_key(self, email):
        """
        Get user by natural key (email).
        
        Args:
            email (str): User's email address
            
        Returns:
            User: User instance
        """
        return self.get(email=email)
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        
        Args:
            email (str): User's email address
            password (str): User's password (optional)
            **extra_fields: Additional fields for the user
            
        Returns:
            User: Created user instance
            
        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError('The Email field must be set')
        
        # Normalize email to lowercase
        email = self.normalize_email(email)
        
        # Set default values
        extra_fields.setdefault('role', 'CITIZEN')
        extra_fields.setdefault('is_active', True)
        
        # Create user instance
        user = self.model(email=email, **extra_fields)
        
        # Set password if provided
        if password:
            user.set_password(password)
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        
        Args:
            email (str): Superuser's email address
            password (str): Superuser's password
            **extra_fields: Additional fields for the superuser
            
        Returns:
            User: Created superuser instance
            
        Raises:
            ValueError: If required superuser fields are not set correctly
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)
    
    def create_staff_user(self, email, password=None, **extra_fields):
        """
        Create and save a staff user with the given email and password.
        
        Args:
            email (str): Staff user's email address
            password (str): Staff user's password
            **extra_fields: Additional fields for the staff user
            
        Returns:
            User: Created staff user instance
        """
        extra_fields.setdefault('role', 'STAFF')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('is_active', True)
        
        return self.create_user(email, password, **extra_fields)
    
    def get_citizens(self):
        """
        Return queryset of all citizen users.
        
        Returns:
            QuerySet: Active citizen users
        """
        return self.filter(role='CITIZEN', is_active=True)
    
    def get_staff(self):
        """
        Return queryset of all staff users.
        
        Returns:
            QuerySet: Active staff users
        """
        return self.filter(role='STAFF', is_active=True)
    
    def get_admins(self):
        """
        Return queryset of all admin users.
        
        Returns:
            QuerySet: Active admin users
        """
        return self.filter(role='ADMIN', is_active=True)
    
    def get_verified_users(self):
        """
        Return queryset of all verified users.
        
        Returns:
            QuerySet: Users with verified email
        """
        return self.filter(email_verified=True, is_active=True)
    
    def get_unverified_users(self):
        """
        Return queryset of all unverified users.
        
        Returns:
            QuerySet: Users with unverified email
        """
        return self.filter(email_verified=False, is_active=True)
    
    def get_locked_users(self):
        """
        Return queryset of all locked users.
        
        Returns:
            QuerySet: Users with locked accounts
        """
        return self.filter(locked_until__gt=timezone.now(), is_active=True)
    
    def get_users_by_phone(self, phone_number):
        """
        Get users by phone number.
        
        Args:
            phone_number (str): Phone number to search for
            
        Returns:
            QuerySet: Users with the specified phone number
        """
        return self.filter(phone_number=phone_number, is_active=True)
    
    def get_users_by_id_number(self, id_number):
        """
        Get users by ID number.
        
        Args:
            id_number (str): ID number to search for
            
        Returns:
            QuerySet: Users with the specified ID number
        """
        return self.filter(id_number=id_number, is_active=True)
    
    def get_recent_users(self, days=30):
        """
        Get users created within the specified number of days.
        
        Args:
            days (int): Number of days to look back
            
        Returns:
            QuerySet: Users created within the specified period
        """
        from django.utils import timezone
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date, is_active=True)
    
    def get_inactive_users(self, days=90):
        """
        Get users who haven't logged in within the specified number of days.
        
        Args:
            days (int): Number of days of inactivity
            
        Returns:
            QuerySet: Inactive users
        """
        from django.utils import timezone
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return self.filter(
            last_login__lt=cutoff_date,
            is_active=True
        )
    
    def search_users(self, query):
        """
        Search users by email, first name, or last name.
        
        Args:
            query (str): Search query
            
        Returns:
            QuerySet: Users matching the search query
        """
        from django.db.models import Q
        
        return self.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query),
            is_active=True
        )
    
    def get_user_statistics(self):
        """
        Get user statistics for reporting.
        
        Returns:
            dict: User statistics
        """
        total_users = self.filter(is_active=True).count()
        citizens = self.get_citizens().count()
        staff = self.get_staff().count()
        admins = self.get_admins().count()
        verified = self.get_verified_users().count()
        unverified = self.get_unverified_users().count()
        locked = self.get_locked_users().count()
        
        return {
            'total_users': total_users,
            'citizens': citizens,
            'staff': staff,
            'admins': admins,
            'verified': verified,
            'unverified': unverified,
            'locked': locked,
            'verification_rate': (verified / total_users * 100) if total_users > 0 else 0,
        }
    
    def bulk_create_users(self, users_data):
        """
        Create multiple users in bulk.
        
        Args:
            users_data (list): List of user data dictionaries
            
        Returns:
            list: Created user instances
        """
        users = []
        for user_data in users_data:
            user = self.model(**user_data)
            users.append(user)
        
        return self.bulk_create(users)
    
    def cleanup_old_unverified_users(self, days=7):
        """
        Delete unverified users older than specified days.
        
        Args:
            days (int): Number of days after which to delete unverified users
            
        Returns:
            int: Number of deleted users
        """
        from django.utils import timezone
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        deleted_count = self.filter(
            email_verified=False,
            created_at__lt=cutoff_date,
            role='CITIZEN'
        ).delete()[0]
        
        return deleted_count
