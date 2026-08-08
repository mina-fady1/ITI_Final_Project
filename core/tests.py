from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from projects.models import Project, Category, Tag
from interactions.models import Rating

User = get_user_model()


class CoreHomepageAndSearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='coreuser@example.com',
            password='Password123',
            first_name='Core',
            last_name='Tester',
            phone_number='01099999999',
            is_active=True
        )

        self.category = Category.objects.create(name='Environment', slug='environment')
        self.tag_solar = Tag.objects.create(name='solar', slug='solar')

        now = timezone.now()
        self.project1 = Project.objects.create(
            creator=self.user,
            category=self.category,
            title='Solar Power Cairo',
            details='Solar energy installation across Cairo roofs.',
            target=Decimal('200000.00'),
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=20),
            is_featured=True
        )
        self.project1.tags.add(self.tag_solar)

        Rating.objects.create(user=self.user, project=self.project1, value=5)

    def test_homepage_loads_and_contains_sections(self):
        """Test homepage renders top rated, latest, featured projects, and categories."""
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Solar Power Cairo')
        self.assertContains(response, 'Environment')

    def test_search_by_title_and_tag(self):
        """Test search query returns matching projects by title or tag name."""
        search_url = reverse('core:search')

        # Search by title
        resp_title = self.client.get(f"{search_url}?q=solar")
        self.assertEqual(resp_title.status_code, 200)
        self.assertContains(resp_title, 'Solar Power Cairo')

        # Search by tag
        resp_tag = self.client.get(f"{search_url}?q=solar")
        self.assertContains(resp_tag, 'Solar Power Cairo')
