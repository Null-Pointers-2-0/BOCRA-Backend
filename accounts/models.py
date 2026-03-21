import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from core.utils import validate_botswana_id_number, validate_botswana_phone_number


class UserRole(models.TextChoices):
    CITIZEN = "CITIZEN", "Citizen / Public"
    REGISTERED = "REGISTERED", "Registered User"
    LICENSEE = "LICENSEE", "Licensee"
    STAFF = "STAFF", "BOCRA Staff"
    ADMIN = "ADMIN", "BOCRA Admin"
    SUPERADMIN = "SUPERADMIN", "Super Admin"


class UserManager(BaseUserManager):
    """
    Custom manager supporting email-based lookups and role-filtered querysets.
    Also extends AbstractUserManager so createsuperuser works via CLI.
    """

    def get_by_natural_key(self, identifier):
        """Support login by either email or username."""
        from django.db.models import Q
        return self.get(Q(email=identifier) | Q(username=identifier))

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.model.normalize_email(email)
        extra_fields.setdefault("role", UserRole.REGISTERED)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.SUPERADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)
        return self.create_user(email, password, **extra_fields)

    def create_staff_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.STAFF)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("email_verified", True)
        return self.create_user(email, password, **extra_fields)

    # ── role-filtered querysets ──────────────────────────────────────────────

    def get_citizens(self):
        return self.filter(role=UserRole.CITIZEN, is_active=True)

    def get_registered(self):
        return self.filter(role=UserRole.REGISTERED, is_active=True)

    def get_licensees(self):
        return self.filter(role=UserRole.LICENSEE, is_active=True)

    def get_staff(self):
        return self.filter(role=UserRole.STAFF, is_active=True)

    def get_admins(self):
        return self.filter(role__in=[UserRole.ADMIN, UserRole.SUPERADMIN], is_active=True)

    def get_verified_users(self):
        return self.filter(email_verified=True, is_active=True)

    def get_unverified_users(self):
        return self.filter(email_verified=False, is_active=True)

    def get_locked_users(self):
        return self.filter(locked_until__gt=timezone.now())

    def get_recent_users(self, days=30):
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(date_joined__gte=cutoff, is_active=True)


_bw_phone_validator = RegexValidator(
    regex=r"^(\+267|267)?[0-9]{8}$",
    message="Enter a valid Botswana phone number (e.g. +26771234567 or 71234567).",
)


class User(AbstractUser):
    """
    BOCRA platform user model.

    Extends Django's AbstractUser so we keep username alongside email.
    Users may log in with either their username or email address.

    Security features:
    - Account lockout after MAX_FAILED_ATTEMPTS failed login attempts
    - Email verification required before full access
    - IP address tracking on each successful login
    """

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_HOURS = 24

    # ── override AbstractUser.id to use UUID ──────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # email is already on AbstractUser but not unique by default
    email = models.EmailField(unique=True, db_index=True)

    # AbstractUser already has: username, first_name, last_name, is_staff,
    # is_active, date_joined, last_login — we just add our custom fields below.

    phone_number = models.CharField(
        max_length=20, blank=True, default="", validators=[_bw_phone_validator]
    )
    id_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="National ID (Omang) or passport number.",
    )
    role = models.CharField(
        max_length=20, choices=UserRole.choices, default=UserRole.REGISTERED, db_index=True
    )
    email_verified = models.BooleanField(default=False, db_index=True)

    # Security / lockout
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    # Soft-delete (on User we keep is_active for Django compatibility,
    # but also store is_deleted so admin purges don't break FK references)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["username"]),
            models.Index(fields=["role"]),
            models.Index(fields=["email_verified"]),
            models.Index(fields=["phone_number"]),
            models.Index(fields=["date_joined"]),
        ]

    def __str__(self):
        return self.email

    # ── computed properties ───────────────────────────────────────────────────

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def is_staff_member(self):
        return self.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN)

    @property
    def is_admin(self):
        return self.role in (UserRole.ADMIN, UserRole.SUPERADMIN)

    @property
    def is_citizen(self):
        return self.role == UserRole.CITIZEN

    @property
    def is_licensee(self):
        return self.role == UserRole.LICENSEE

    @property
    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    # ── account management methods ────────────────────────────────────────────

    def verify_email(self):
        self.email_verified = True
        self.save(update_fields=["email_verified"])

    def lock_account(self, hours=None):
        hours = hours or self.LOCKOUT_HOURS
        self.locked_until = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=["locked_until"])

    def unlock_account(self):
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=["locked_until", "failed_login_attempts"])

    def increment_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= self.MAX_FAILED_ATTEMPTS:
            self.lock_account()
        else:
            self.save(update_fields=["failed_login_attempts"])

    def reset_failed_login(self):
        if self.failed_login_attempts > 0:
            self.failed_login_attempts = 0
            self.save(update_fields=["failed_login_attempts"])

    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "is_active", "deleted_at"])

    # ── permission helpers ────────────────────────────────────────────────────

    def can_view_licences(self):
        return self.role in (
            UserRole.LICENSEE, UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN
        )

    def can_process_licences(self):
        return self.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN)

    def can_manage_users(self):
        return self.role in (UserRole.ADMIN, UserRole.SUPERADMIN)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.phone_number and not validate_botswana_phone_number(self.phone_number):
            raise ValidationError({"phone_number": "Invalid Botswana phone number."})
        if self.id_number and not validate_botswana_id_number(self.id_number):
            raise ValidationError({"id_number": "Invalid Botswana ID or passport number."})


class Profile(models.Model):
    """
    Extended profile for a User.
    Merged from both data-models.md spec and friend implementation:
    professional info (org, position) + personal info (DoB, gender, bio).
    """

    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"
        PREFER_NOT = "N", "Prefer not to say"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Professional / organisational
    organisation = models.CharField(max_length=255, blank=True, default="")
    position = models.CharField(max_length=150, blank=True, default="")

    # Personal
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=1, choices=Gender.choices, blank=True, default=""
    )
    bio = models.TextField(blank=True, default="")

    # Location
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=100, default="Botswana")

    # Identification (encrypted at DB level where possible)
    id_number = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Omang or passport — mirrored from User for profile completeness checks."
    )

    # Media
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_profile"

    def __str__(self):
        return f"Profile({self.user.email})"

    @property
    def age(self):
        from core.utils import calculate_age
        return calculate_age(self.date_of_birth) if self.date_of_birth else None

    @property
    def is_complete(self):
        """True when all key profile fields are filled."""
        return all([
            self.organisation or self.user.role not in (UserRole.LICENSEE, UserRole.REGISTERED),
            self.address,
            self.city,
        ])
