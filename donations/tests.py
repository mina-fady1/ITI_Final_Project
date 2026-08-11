from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from projects.models import Project, Category
from projects.services import cancel_project
from .models import Donation

User = get_user_model()


class DonationsAndCancellationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.creator = User.objects.create_user(
            email='creator@example.com',
            password='Password123',
            first_name='Creator',
            last_name='User',
            phone_number='01011111111',
            is_active=True
        )
        self.donor = User.objects.create_user(
            email='donor@example.com',
            password='Password123',
            first_name='Donor',
            last_name='User',
            phone_number='01222222222',
            is_active=True
        )

        self.category = Category.objects.create(name='Education', slug='education')

        now = timezone.now()
        self.project = Project.objects.create(
            creator=self.creator,
            category=self.category,
            title='Cairo Tech School',
            details='Funding tech school in Cairo.',
            target=Decimal('100000.00'),
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=30)
        )

    def test_positive_donation_updates_totals(self):
        """Test valid donation updates total donations and funding percentage."""
        self.client.force_login(self.donor)
        donate_url = reverse('donations:donate', kwargs={'pk': self.project.pk})
        
        response = self.client.post(donate_url, {'amount': '15000.00'})
        self.assertEqual(response.status_code, 302)
        
        self.assertEqual(self.project.total_donations, Decimal('15000.00'))
        self.assertEqual(self.project.funding_percentage, Decimal('15.00'))
        self.assertEqual(self.project.remaining_amount, Decimal('85000.00'))

    def test_negative_or_zero_donation_rejected(self):
        """Test zero or negative donation is rejected."""
        self.client.force_login(self.donor)
        donate_url = reverse('donations:donate', kwargs={'pk': self.project.pk})
        
        response = self.client.post(donate_url, {'amount': '-500.00'}, follow=True)
        self.assertEqual(self.project.total_donations, Decimal('0.00'))

    def test_creator_cannot_donate_to_own_project(self):
        """Test project creators are prevented from donating to their own campaigns."""
        self.client.force_login(self.creator)
        donate_url = reverse('donations:donate', kwargs={'pk': self.project.pk})

        response = self.client.post(donate_url, {'amount': '1000.00'}, follow=True)
        self.assertEqual(self.project.total_donations, Decimal('0.00'))

    def test_25_percent_boundary_rule(self):
        """
        PDF Rule Test:
        Project creator can cancel ONLY if donations < 25% of target.
        Target = 100,000 EGP. 25% = 25,000 EGP.
        - 24,999.99 EGP -> allowed
        - 25,000.00 EGP -> rejected
        - 25,000.01 EGP -> rejected
        """
        # Case A: 24,999.99 EGP (< 25%) -> Cancellation Allowed
        d1 = Donation.objects.create(user=self.donor, project=self.project, amount=Decimal('24999.99'))
        self.assertTrue(cancel_project(self.project, self.creator))
        
        # Reset project for boundary testing
        self.project.is_cancelled = False
        self.project.save()
        d1.delete()

        # Case B: 25,000.00 EGP (= 25%) -> Cancellation REJECTED
        d2 = Donation.objects.create(user=self.donor, project=self.project, amount=Decimal('25000.00'))
        with self.assertRaises(ValidationError):
            cancel_project(self.project, self.creator)
            
        d2.delete()

        # Case C: 25,000.01 EGP (> 25%) -> Cancellation REJECTED
        Donation.objects.create(user=self.donor, project=self.project, amount=Decimal('25000.01'))
        with self.assertRaises(ValidationError):
            cancel_project(self.project, self.creator)
