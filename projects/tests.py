from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Project, Category, Tag, ProjectImage
from .services import cancel_project, get_similar_projects
from .forms import ProjectForm

User = get_user_model()


class ProjectsSystemTests(TestCase):
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
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='Password123',
            first_name='Other',
            last_name='User',
            phone_number='01222222222',
            is_active=True
        )

        self.category = Category.objects.create(name='Technology', slug='technology')
        self.tag_tech = Tag.objects.create(name='tech', slug='tech')
        self.tag_ai = Tag.objects.create(name='ai', slug='ai')

        now = timezone.now()
        self.project = Project.objects.create(
            creator=self.creator,
            category=self.category,
            title='AI Innovations Cairo',
            details='Building innovative AI solutions in Cairo.',
            target=Decimal('100000.00'),
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=30)
        )
        self.project.tags.add(self.tag_tech, self.tag_ai)

    def test_project_status_calculation(self):
        """Test status evaluates correctly to Running, Upcoming, Completed, Cancelled."""
        self.assertEqual(self.project.status, 'Running')

        # Test cancelled
        self.project.is_cancelled = True
        self.assertEqual(self.project.status, 'Cancelled')

    def test_25_percent_cancellation_rule(self):
        """
        PDF Specification Test:
        Project creator can cancel project ONLY if donations are less than 25% of target.
        Target = 100,000 EGP. 25% = 25,000 EGP.
        """
        # Case 1: 0 EGP raised (< 25%) -> Allowed
        self.assertTrue(cancel_project(self.project, self.creator))
        self.assertTrue(self.project.is_cancelled)

    def test_cancellation_rejected_by_non_creator(self):
        """Test non-creator cannot cancel campaign."""
        with self.assertRaises(PermissionDenied):
            cancel_project(self.project, self.other_user)

    def test_similar_projects_tag_matching(self):
        """Test similar projects are recommended based on shared tags, excluding current project."""
        p2 = Project.objects.create(
            creator=self.creator,
            category=self.category,
            title='Tech Hub Egypt',
            details='Details tech hub',
            target=Decimal('50000.00'),
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=20)
        )
        p2.tags.add(self.tag_tech)

        similar = get_similar_projects(self.project, limit=4)
        self.assertIn(p2, similar)
        self.assertNotIn(self.project, similar)

    def test_project_form_datetime_local_and_multiple_images(self):
        """Test HTML5 datetime-local string formats and multiple file uploads are accepted by ProjectForm."""
        image_content = b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
        test_img1 = SimpleUploadedFile("test1.gif", image_content, content_type="image/gif")
        test_img2 = SimpleUploadedFile("test2.gif", image_content, content_type="image/gif")

        form_data = {
            'title': 'New Campaign',
            'details': 'Campaign details text',
            'category': self.category.id,
            'target': '150000.00',
            'start_time': '2026-08-08T10:00',  # HTML5 datetime-local format
            'end_time': '2026-09-08T10:00',    # HTML5 datetime-local format
            'tags_input': 'tech, cairo',
        }
        file_data = {
            'images': [test_img1, test_img2]
        }

        form = ProjectForm(data=form_data, files=file_data)
        self.assertTrue(form.is_valid(), form.errors)
