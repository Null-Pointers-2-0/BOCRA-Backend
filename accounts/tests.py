"""
Tests for the accounts app.

Test groups
───────────
UserModelTests            — User model methods (full_name, is_locked, verify_email, lockout)
ProfileTests              — Profile auto-creation, is_complete property
UserManagerTests          — Custom manager filtered querysets
RegisterViewTests         — POST /api/v1/accounts/register/
EmailVerificationTests    — GET  /api/v1/accounts/verify-email/
LoginViewTests            — POST /api/v1/accounts/login/
LogoutViewTests           — POST /api/v1/accounts/logout/
ProfileViewTests          — GET/PATCH /api/v1/accounts/profile/
PasswordChangeTests       — POST /api/v1/accounts/change-password/
PasswordResetTests        — POST /api/v1/accounts/password-reset/
AdminUserViewTests        — GET /api/v1/accounts/users/ and /users/<pk>/
PermissionsTests          — IsStaff, IsAdmin, IsCitizen, IsOwnerOrStaff
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Profile, UserRole
from accounts.permissions import IsAdmin, IsCitizen, IsOwner, IsOwnerOrStaff, IsStaff

User = get_user_model()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def create_user(
    email="user@example.com",
    username="regularuser",
    password="TestPass123!",
    role=UserRole.REGISTERED,
    verified=True,
    **kwargs,
):
    user = User.objects.create_user(
        email=email,
        username=username,
        first_name="Test",
        last_name="User",
        password=password,
        role=role,
        **kwargs,
    )
    if verified:
        user.verify_email()
    return user


def create_staff(email="staff@bocra.bw", username="staffuser"):
    return create_user(email=email, username=username, role=UserRole.STAFF)


def create_admin(email="admin@bocra.bw", username="adminuser"):
    return create_user(email=email, username=username, role=UserRole.ADMIN)


def auth_client(user) -> APIClient:
    """Return an APIClient pre-authenticated with user's JWT."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


# ─── User Model ───────────────────────────────────────────────────────────────

class UserModelTests(APITestCase):

    def test_full_name_first_last(self):
        user = create_user()
        self.assertEqual(user.full_name, "Test User")

    def test_full_name_falls_back_to_username(self):
        user = create_user()
        user.first_name = ""
        user.last_name = ""
        user.save()
        self.assertEqual(user.full_name, user.username)

    def test_str_is_email(self):
        user = create_user()
        self.assertEqual(str(user), "user@example.com")

    def test_is_locked_false_by_default(self):
        user = create_user()
        self.assertFalse(user.is_locked)

    def test_lock_account_sets_locked_until(self):
        user = create_user()
        user.lock_account(hours=1)
        self.assertTrue(user.is_locked)

    def test_unlock_expired_lock(self):
        user = create_user()
        user.locked_until = timezone.now() - timezone.timedelta(hours=1)
        user.save()
        self.assertFalse(user.is_locked)

    def test_verify_email(self):
        user = create_user(verified=False)
        self.assertFalse(user.email_verified)
        user.verify_email()
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_is_staff_member_roles(self):
        for role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPERADMIN):
            user = create_user(email=f"{role}@test.com", username=f"user_{role}", role=role)
            self.assertTrue(user.is_staff_member)

    def test_is_staff_member_false_for_citizen(self):
        user = create_user(role=UserRole.CITIZEN)
        self.assertFalse(user.is_staff_member)

    def test_failed_login_increments(self):
        user = create_user()
        initial = user.failed_login_attempts
        user.increment_failed_login()
        user.refresh_from_db()
        self.assertEqual(user.failed_login_attempts, initial + 1)

    def test_reset_failed_login(self):
        user = create_user()
        user.failed_login_attempts = 3
        user.save()
        user.reset_failed_login()
        user.refresh_from_db()
        self.assertEqual(user.failed_login_attempts, 0)

    def test_account_locks_after_max_attempts(self):
        user = create_user()
        for _ in range(User.MAX_FAILED_ATTEMPTS):
            user.increment_failed_login()
        user.refresh_from_db()
        self.assertTrue(user.is_locked)


class ProfileTests(APITestCase):

    def test_profile_auto_created(self):
        user = create_user()
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_is_complete_false_by_default(self):
        user = create_user()
        self.assertFalse(user.profile.is_complete)


# ─── UserManager ──────────────────────────────────────────────────────────────

class UserManagerTests(APITestCase):

    def setUp(self):
        self.citizen = create_user(email="c@test.com", username="citizen", role=UserRole.CITIZEN)
        self.staff = create_staff()
        self.admin = create_admin()

    def test_get_staff_returns_only_staff(self):
        staff_qs = User.objects.get_staff()
        self.assertIn(self.staff, staff_qs)
        self.assertNotIn(self.citizen, staff_qs)

    def test_get_citizens_returns_only_citizens(self):
        qs = User.objects.get_citizens()
        self.assertIn(self.citizen, qs)
        self.assertNotIn(self.staff, qs)

    def test_get_admins(self):
        qs = User.objects.get_admins()
        self.assertIn(self.admin, qs)
        self.assertNotIn(self.citizen, qs)

    def test_get_verified_users(self):
        unverified = create_user(email="unv@test.com", username="unverified", verified=False)
        qs = User.objects.get_verified_users()
        self.assertNotIn(unverified, qs)

    def test_create_superuser(self):
        su = User.objects.create_superuser(email="su@test.com", password="Pass123!")
        self.assertTrue(su.is_superuser)
        self.assertTrue(su.is_staff)
        self.assertTrue(su.email_verified)


# ─── Registration ─────────────────────────────────────────────────────────────

class RegisterViewTests(APITestCase):

    url = "/api/v1/accounts/register/"

    def valid_payload(self, **overrides):
        data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        data.update(overrides)
        return data

    @patch("accounts.views.send_verification_email.delay")
    def test_register_success(self, mock_email):
        response = self.client.post(self.url, self.valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.json()["success"])
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    @patch("accounts.views.send_verification_email.delay")
    def test_register_creates_profile(self, mock_email):
        self.client.post(self.url, self.valid_payload(), format="json")
        user = User.objects.get(email="newuser@example.com")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_register_missing_email(self):
        payload = self.valid_payload()
        del payload["email"]
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        payload = self.valid_payload(confirm_password="WrongPass!")
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.send_verification_email.delay")
    def test_register_duplicate_email(self, mock_email):
        self.client.post(self.url, self.valid_payload(), format="json")
        response = self.client.post(self.url, self.valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_phone(self):
        payload = self.valid_payload(phone_number="123")
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.views.send_verification_email.delay")
    def test_new_user_not_verified(self, mock_email):
        self.client.post(self.url, self.valid_payload(), format="json")
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.email_verified)

    @patch("accounts.views.send_verification_email.delay")
    def test_register_default_role_is_registered(self, mock_email):
        self.client.post(self.url, self.valid_payload(), format="json")
        user = User.objects.get(email="newuser@example.com")
        self.assertEqual(user.role, UserRole.REGISTERED)


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginViewTests(APITestCase):

    url = "/api/v1/accounts/login/"

    def setUp(self):
        self.user = create_user()

    def test_login_success_with_email(self):
        response = self.client.post(
            self.url,
            {"identifier": "user@example.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertIn("access", data)
        self.assertIn("refresh", data)

    def test_login_success_with_username(self):
        response = self.client.post(
            self.url,
            {"identifier": "regularuser", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_wrong_password(self):
        response = self.client.post(
            self.url,
            {"identifier": "user@example.com", "password": "wrongpass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        response = self.client.post(
            self.url,
            {"identifier": "nobody@example.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_locked_account_rejected(self):
        self.user.lock_account(hours=24)
        response = self.client.post(
            self.url,
            {"identifier": "user@example.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url,
            {"identifier": "user@example.com", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_failed_login_increments_counter(self):
        self.client.post(
            self.url,
            {"identifier": "user@example.com", "password": "badpass"},
            format="json",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 1)

    def test_successful_login_resets_counter(self):
        self.user.failed_login_attempts = 3
        self.user.save()
        self.client.post(
            self.url,
            {"identifier": "user@example.com", "password": "TestPass123!"},
            format="json",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.failed_login_attempts, 0)


# ─── Logout ───────────────────────────────────────────────────────────────────

class LogoutViewTests(APITestCase):

    url = "/api/v1/accounts/logout/"

    def setUp(self):
        self.user = create_user()
        self.client = auth_client(self.user)
        self.refresh = str(RefreshToken.for_user(self.user))

    def test_logout_success(self):
        response = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_requires_auth(self):
        anon = APIClient()
        response = anon.post(self.url, {"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_token_returns_400(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ─── Profile ──────────────────────────────────────────────────────────────────

class ProfileViewTests(APITestCase):

    url = "/api/v1/accounts/profile/"

    def setUp(self):
        self.user = create_user()
        self.client = auth_client(self.user)

    def test_get_profile_authenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["email"], "user@example.com")

    def test_get_profile_unauthenticated(self):
        anon = APIClient()
        response = anon.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_profile_updates_name(self):
        response = self.client.patch(
            self.url,
            {"first_name": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")

    def test_patch_invalid_phone_rejected(self):
        response = self.client.patch(
            self.url,
            {"phone_number": "notaphone"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ─── Password Change ──────────────────────────────────────────────────────────

class PasswordChangeTests(APITestCase):

    url = "/api/v1/accounts/change-password/"

    def setUp(self):
        self.user = create_user()
        self.client = auth_client(self.user)

    def test_change_password_success(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "TestPass123!",
                "new_password": "NewStrongPass456!",
                "confirm_password": "NewStrongPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_wrong_old_password_rejected(self):
        response = self.client.post(
            self.url,
            {
                "current_password": "WrongOld!",
                "new_password": "NewStrongPass456!",
                "confirm_password": "NewStrongPass456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_password_mismatch_rejected(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "TestPass123!",
                "new_password": "NewStrongPass456!",
                "confirm_password": "Mismatch!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_authentication(self):
        anon = APIClient()
        response = anon.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─── Password Reset Request ───────────────────────────────────────────────────

class PasswordResetTests(APITestCase):

    request_url = "/api/v1/accounts/password-reset/"

    def setUp(self):
        self.user = create_user()

    @patch("accounts.views.send_password_reset_email.delay")
    def test_reset_request_always_returns_200(self, mock_email):
        response = self.client.post(
            self.request_url,
            {"email": "user@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("accounts.views.send_password_reset_email.delay")
    def test_reset_request_nonexistent_email_still_200(self, mock_email):
        response = self.client.post(
            self.request_url,
            {"email": "nobody@fakesite.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reset_request_invalid_email_400(self):
        response = self.client.post(
            self.request_url,
            {"email": "notanemail"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ─── Admin User Management ────────────────────────────────────────────────────

class AdminUserViewTests(APITestCase):

    list_url = "/api/v1/accounts/users/"

    def setUp(self):
        self.admin = create_admin()
        self.regular = create_user(email="reg@test.com", username="reguser")
        self.admin_client = auth_client(self.admin)

    def test_admin_can_list_users(self):
        response = self.admin_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_list_users(self):
        regular_client = auth_client(self.regular)
        response = regular_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_users(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_get_user_detail(self):
        url = f"/api/v1/accounts/users/{self.regular.id}/"
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_update_user_role(self):
        url = f"/api/v1/accounts/users/{self.regular.id}/"
        response = self.admin_client.patch(url, {"role": UserRole.STAFF}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.role, UserRole.STAFF)

    def test_filter_by_role(self):
        response = self.admin_client.get(self.list_url, {"role": UserRole.ADMIN})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ─── Permissions ──────────────────────────────────────────────────────────────

class PermissionsTests(APITestCase):
    """Test that RBAC permission classes accept/reject the right users."""

    def _make_request(self, user=None):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        req = factory.get("/")
        if user:
            req.user = user
        else:
            from django.contrib.auth.models import AnonymousUser
            req.user = AnonymousUser()
        return req

    def test_is_staff_allows_staff_role(self):
        perm = IsStaff()
        user = create_staff(email="s2@test.com", username="s2")
        req = self._make_request(user)
        self.assertTrue(perm.has_permission(req, None))

    def test_is_staff_rejects_regular_user(self):
        perm = IsStaff()
        user = create_user(email="r2@test.com", username="r2")
        req = self._make_request(user)
        self.assertFalse(perm.has_permission(req, None))

    def test_is_admin_allows_admin_role(self):
        perm = IsAdmin()
        user = create_admin(email="a2@test.com", username="a2")
        req = self._make_request(user)
        self.assertTrue(perm.has_permission(req, None))

    def test_is_admin_rejects_staff_role(self):
        perm = IsAdmin()
        user = create_staff(email="s3@test.com", username="s3")
        req = self._make_request(user)
        self.assertFalse(perm.has_permission(req, None))

    def test_is_citizen_allows_citizen(self):
        perm = IsCitizen()
        user = create_user(email="ct@test.com", username="ct", role=UserRole.CITIZEN)
        req = self._make_request(user)
        self.assertTrue(perm.has_permission(req, None))

    def test_is_citizen_rejects_registered(self):
        perm = IsCitizen()
        user = create_user(email="ct2@test.com", username="ct2", role=UserRole.REGISTERED)
        req = self._make_request(user)
        self.assertFalse(perm.has_permission(req, None))
