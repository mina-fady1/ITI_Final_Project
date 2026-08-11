from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from .models import ActivationToken, PasswordResetToken

User = get_user_model()


class AccountsSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.profile_url = reverse('accounts:profile')
        self.edit_profile_url = reverse('accounts:edit_profile')
        self.delete_account_url = reverse('accounts:delete_account')

        self.valid_user_data = {
            'first_name': 'Ahmed',
            'last_name': 'Hassan',
            'email': 'ahmed@example.com',
            'phone_number': '01012345678',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123'
        }

    def test_registration_creates_inactive_user_and_token(self):
        """Test registration creates inactive user and an activation token."""
        response = self.client.post(self.register_url, self.valid_user_data)
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(email='ahmed@example.com')
        self.assertFalse(user.is_active)
        self.assertTrue(ActivationToken.objects.filter(user=user).exists())

    def test_invalid_egyptian_phone_rejected(self):
        """Test non-Egyptian phone numbers are rejected by validator."""
        invalid_data = self.valid_user_data.copy()
        invalid_data['phone_number'] = '01912345678'  # 019 is invalid
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'phone_number', 'Enter a valid Egyptian mobile number starting with 010, 011, 012, or 015 followed by 8 digits (e.g. 01012345678).')

    def test_inactive_user_cannot_login(self):
        """Test unactivated user cannot log in."""
        self.client.post(self.register_url, self.valid_user_data)
        response = self.client.post(self.login_url, {
            'email': 'ahmed@example.com',
            'password': 'StrongPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], None, 'Your account is not activated yet. Please check your email for the activation link.')

    def test_activation_link_flow_and_expiration(self):
        """Test activation succeeds within 24h."""
        self.client.post(self.register_url, self.valid_user_data)
        user = User.objects.get(email='ahmed@example.com')
        token = ActivationToken.objects.get(user=user)

        activate_url = reverse('accounts:activate', kwargs={'token': token.token})
        response = self.client.get(activate_url)
        self.assertEqual(response.status_code, 302)
        
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_expired_activation_token_fails(self):
        """Test activation token older than 24 hours fails and removes user."""
        self.client.post(self.register_url, self.valid_user_data)
        user = User.objects.get(email='ahmed@example.com')
        token = ActivationToken.objects.get(user=user)

        # Backdate token by 25 hours
        token.created_at = timezone.now() - timedelta(hours=25)
        token.save()

        activate_url = reverse('accounts:activate', kwargs={'token': token.token})
        response = self.client.get(activate_url, follow=True)
        self.assertFalse(User.objects.filter(email='ahmed@example.com').exists())

    def test_account_deletion_with_password(self):
        """Test account deletion requires correct password."""
        user = User.objects.create_user(
            email='delete_me@example.com',
            password='MySecurePassword123',
            first_name='Test',
            last_name='Delete',
            phone_number='01112345678',
            is_active=True
        )
        self.client.force_login(user)

        # Submit wrong password -> fails
        resp_fail = self.client.post(self.delete_account_url, {'password': 'WrongPassword'})
        self.assertEqual(resp_fail.status_code, 200)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

        # Submit correct password -> succeeds
        resp_success = self.client.post(self.delete_account_url, {'password': 'MySecurePassword123'})
        self.assertEqual(resp_success.status_code, 302)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())


class PasswordResetTests(TestCase):
    """Tests for the Forgot Password / Reset Password bonus feature."""

    def setUp(self):
        self.client = Client()
        self.forgot_password_url = reverse('accounts:forgot_password')
        self.login_url = reverse('accounts:login')

        self.user = User.objects.create_user(
            email='reset_me@example.com',
            password='OldPassword123',
            first_name='Reset',
            last_name='Me',
            phone_number='01212345678',
            is_active=True
        )

    def test_forgot_password_unknown_email_rejected(self):
        """An email with no matching account should not be accepted."""
        response = self.client.post(self.forgot_password_url, {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'No account is associated with this email address.')
        self.assertFalse(PasswordResetToken.objects.exists())

    def test_forgot_password_creates_token_and_sends_email(self):
        """A valid email should create a PasswordResetToken and send an email."""
        response = self.client.post(self.forgot_password_url, {'email': 'reset_me@example.com'})
        self.assertEqual(response.status_code, 302)

        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset_me@example.com', mail.outbox[0].to)

    def test_reset_password_with_valid_token_succeeds(self):
        """A valid, unused, unexpired token should let the user set a new password."""
        token = PasswordResetToken.objects.create(user=self.user)
        reset_url = reverse('accounts:reset_password', kwargs={'token': token.token})

        response = self.client.post(reset_url, {
            'new_password': 'BrandNewPassword123',
            'confirm_new_password': 'BrandNewPassword123'
        })
        self.assertEqual(response.status_code, 302)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPassword123'))

        token.refresh_from_db()
        self.assertTrue(token.used)

        # The old password should no longer work
        login_ok = self.client.login(email='reset_me@example.com', password='OldPassword123')
        self.assertFalse(login_ok)

    def test_reset_password_mismatched_passwords_rejected(self):
        """Mismatched new password / confirmation should be rejected."""
        token = PasswordResetToken.objects.create(user=self.user)
        reset_url = reverse('accounts:reset_password', kwargs={'token': token.token})

        response = self.client.post(reset_url, {
            'new_password': 'BrandNewPassword123',
            'confirm_new_password': 'SomethingElse123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'confirm_new_password', 'Passwords do not match.')

    def test_expired_reset_token_rejected(self):
        """A token older than 1 hour should no longer work."""
        token = PasswordResetToken.objects.create(user=self.user)
        token.created_at = timezone.now() - timedelta(hours=2)
        token.save()

        reset_url = reverse('accounts:reset_password', kwargs={'token': token.token})
        response = self.client.get(reset_url, follow=True)
        self.assertRedirects(response, self.forgot_password_url)

    def test_used_reset_token_cannot_be_reused(self):
        """A token that was already used once should be rejected on a second attempt."""
        token = PasswordResetToken.objects.create(user=self.user)
        reset_url = reverse('accounts:reset_password', kwargs={'token': token.token})

        # First use succeeds
        self.client.post(reset_url, {
            'new_password': 'FirstNewPassword123',
            'confirm_new_password': 'FirstNewPassword123'
        })

        # Second attempt with the same token should be rejected
        response = self.client.get(reset_url, follow=True)
        self.assertRedirects(response, self.forgot_password_url)

    def test_invalid_token_rejected(self):
        """A token that doesn't exist at all should redirect to forgot_password."""
        fake_token = '11111111-1111-1111-1111-111111111111'
        reset_url = reverse('accounts:reset_password', kwargs={'token': fake_token})
        response = self.client.get(reset_url, follow=True)
        self.assertRedirects(response, self.forgot_password_url)


class CompleteProfileMiddlewareTests(TestCase):
    """
    Tests for CompleteProfileMiddleware, which forces users created via
    Facebook (no phone_number) to complete their profile before using
    the rest of the site.
    """

    def setUp(self):
        self.client = Client()
        self.edit_profile_url = reverse('accounts:edit_profile')
        self.profile_url = reverse('accounts:profile')
        self.logout_url = reverse('accounts:logout')

        # Simulates a user created by CustomSocialAccountAdapter via Facebook:
        # active immediately, but with no phone_number.
        self.social_user = User.objects.create(
            email='fbuser@example.com',
            first_name='FB',
            last_name='User',
            phone_number='',
            is_active=True
        )
        self.social_user.set_unusable_password()
        self.social_user.save()

    def test_user_without_phone_is_redirected_to_edit_profile(self):
        """Any page other than edit_profile/logout should redirect to edit_profile."""
        self.client.force_login(self.social_user)
        response = self.client.get(self.profile_url, follow=True)
        self.assertRedirects(response, self.edit_profile_url)

    def test_user_without_phone_can_still_access_edit_profile(self):
        """edit_profile itself must stay reachable, or the redirect would loop forever."""
        self.client.force_login(self.social_user)
        response = self.client.get(self.edit_profile_url)
        self.assertEqual(response.status_code, 200)

    def test_user_without_phone_can_still_logout(self):
        """logout must stay reachable so the user isn't trapped in the account."""
        self.client.force_login(self.social_user)
        response = self.client.get(self.logout_url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_completing_phone_number_lifts_the_redirect(self):
        """Once phone_number is set, the user should be able to browse normally."""
        self.client.force_login(self.social_user)

        self.social_user.phone_number = '01098765432'
        self.social_user.save()

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)

    def test_normal_user_with_phone_is_never_redirected(self):
        """A regular (non-Facebook) active user should never hit this redirect."""
        normal_user = User.objects.create_user(
            email='normal@example.com',
            password='SomePassword123',
            first_name='Normal',
            last_name='User',
            phone_number='01098765432',
            is_active=True
        )
        self.client.force_login(normal_user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
