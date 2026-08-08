from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ActivationToken

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
