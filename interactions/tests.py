from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from projects.models import Project, Category
from .models import Comment, Rating, Report

User = get_user_model()


class InteractionsSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='Password123',
            first_name='User',
            last_name='One',
            phone_number='01011111111',
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='Password123',
            first_name='User',
            last_name='Two',
            phone_number='01222222222',
            is_active=True
        )

        self.category = Category.objects.create(name='Art', slug='art')
        now = timezone.now()
        self.project = Project.objects.create(
            creator=self.user1,
            category=self.category,
            title='Egyptian Art Exhibition',
            details='Funding art exhibition in Alexandria.',
            target=Decimal('50000.00'),
            start_time=now - timedelta(days=1),
            end_time=now + timedelta(days=30)
        )

    def test_comment_creation_and_nested_reply(self):
        """Test creating comments, nested replies, and owner-only deletion."""
        self.client.force_login(self.user1)
        add_comment_url = reverse('interactions:add_comment', kwargs={'pk': self.project.pk})

        # Post root comment
        self.client.post(add_comment_url, {'content': 'Great initiative!'})
        comment = Comment.objects.get(project=self.project, parent=None)
        self.assertEqual(comment.content, 'Great initiative!')

        # Post nested reply
        self.client.force_login(self.user2)
        self.client.post(add_comment_url, {
            'content': 'I agree!',
            'parent_id': str(comment.id)
        })
        reply = Comment.objects.get(parent=comment)
        self.assertEqual(reply.user, self.user2)

        # Non-owner cannot delete user1 comment
        delete_url = reverse('interactions:delete_comment', kwargs={'pk': comment.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 403)  # PermissionDenied

    def test_nested_reply_flattens_to_top_level_parent(self):
        """Test replying to a reply attaches to top-level comment parent."""
        self.client.force_login(self.user1)
        add_comment_url = reverse('interactions:add_comment', kwargs={'pk': self.project.pk})

        self.client.post(add_comment_url, {'content': 'Root Comment'})
        root = Comment.objects.get(parent=None)

        self.client.post(add_comment_url, {'content': 'Reply 1', 'parent_id': str(root.id)})
        reply1 = Comment.objects.get(content='Reply 1')

        # Reply to reply1 -> should attach to root
        self.client.post(add_comment_url, {'content': 'Reply 2', 'parent_id': str(reply1.id)})
        reply2 = Comment.objects.get(content='Reply 2')
        self.assertEqual(reply2.parent, root)

    def test_rating_uniqueness_and_average(self):
        """Test one rating per user, rating update, and average rating calculation."""
        self.client.force_login(self.user1)
        rate_url = reverse('interactions:rate_project', kwargs={'pk': self.project.pk})

        # User1 rates 4 stars
        self.client.post(rate_url, {'value': '4'})
        self.assertEqual(self.project.ratings_count, 1)
        self.assertEqual(self.project.average_rating, 4.0)

        # User1 updates rating to 5 stars
        self.client.post(rate_url, {'value': '5'})
        self.assertEqual(self.project.ratings_count, 1)
        self.assertEqual(self.project.average_rating, 5.0)

        # User2 rates 3 stars
        self.client.force_login(self.user2)
        self.client.post(rate_url, {'value': '3'})
        self.assertEqual(self.project.ratings_count, 2)
        self.assertEqual(self.project.average_rating, 4.0)  # (5+3)/2 = 4.0

    def test_reporting_system(self):
        """Test reporting projects and comments."""
        self.client.force_login(self.user2)
        report_proj_url = reverse('interactions:report_project', kwargs={'pk': self.project.pk})
        
        self.client.post(report_proj_url, {'reason': 'Inappropriate title.'})
        self.assertTrue(Report.objects.filter(project=self.project, user=self.user2).exists())
