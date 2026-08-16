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


import json
from unittest.mock import patch, MagicMock
from core.chatbot_engine import (
    sanitize_chat_history,
    get_platform_live_context,
    get_offline_fallback_response,
    generate_chatbot_reply
)


class ChatbotSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='botuser@example.com',
            password='Password123',
            first_name='Bot',
            last_name='Tester',
            phone_number='01011112222',
            is_active=True
        )
        self.category = Category.objects.create(name='Technology', slug='technology')
        self.now = timezone.now()
        self.project = Project.objects.create(
            creator=self.user,
            category=self.category,
            title='AI Education Initiative',
            details='Providing AI education to students across Egypt.',
            target=Decimal('50000.00'),
            start_time=self.now - timedelta(days=2),
            end_time=self.now + timedelta(days=28),
            is_featured=True
        )

    def test_chatbot_endpoint_rejects_get(self):
        """Chatbot endpoint should only accept POST requests."""
        response = self.client.get(reverse('core:chatbot'))
        self.assertEqual(response.status_code, 405)

    def test_chatbot_endpoint_rejects_empty_message(self):
        """Chatbot endpoint should reject empty messages with 400."""
        response = self.client.post(
            reverse('core:chatbot'),
            data=json.dumps({'message': '   '}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_chatbot_endpoint_rejects_invalid_json(self):
        """Chatbot endpoint should reject malformed JSON with 400."""
        response = self.client.post(
            reverse('core:chatbot'),
            data="not-a-valid-json",
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_history_sanitization_removes_duplicate_user_turns(self):
        """Chat history should remove trailing duplicate user messages and enforce alternating roles."""
        history = [
            {'sender': 'user', 'text': 'Hello'},
            {'sender': 'bot', 'text': 'Hi! How can I help?'},
            {'sender': 'user', 'text': 'How to donate?'}
        ]
        sanitized = sanitize_chat_history(history, 'How to donate?')
        
        # Last turn in contents must be the current user message, no duplicate preceding user message
        self.assertEqual(sanitized[-1]['role'], 'user')
        self.assertEqual(sanitized[-1]['parts'][0]['text'], 'How to donate?')
        # The preceding turn should be model
        if len(sanitized) > 1:
            self.assertEqual(sanitized[-2]['role'], 'model')

    def test_platform_live_context_contains_database_info(self):
        """get_platform_live_context must reflect real database projects and categories."""
        context = get_platform_live_context('education')
        self.assertIn('AI Education Initiative', context)
        self.assertIn('Technology', context)
        self.assertIn('EGP', context)

    def test_offline_fallback_cancellation_policy(self):
        """Offline fallback accurately explains the 25% cancellation rule."""
        response_text = get_offline_fallback_response("Can I cancel my campaign after getting donations?")
        self.assertIn('25%', response_text)
        self.assertIn('Cancellation', response_text)

    def test_offline_fallback_donation_guide(self):
        """Offline fallback explains the donation process and links to projects."""
        response_text = get_offline_fallback_response("How to donate?")
        self.assertIn('/projects/', response_text)
        self.assertIn('Donate', response_text)

    def test_offline_fallback_campaign_creation(self):
        """Offline fallback explains campaign creation rules."""
        response_text = get_offline_fallback_response("How to create a campaign?")
        self.assertIn('/projects/create/', response_text)
        self.assertIn('Target (EGP)', response_text)

    def test_offline_fallback_phone_validation_info(self):
        """Offline fallback explains the 010/011/012/015 Egyptian phone requirement."""
        response_text = get_offline_fallback_response("What are phone number rules for registration?")
        self.assertIn('010', response_text)
        self.assertIn('11 digits', response_text)

    @patch('core.chatbot_engine.requests.post')
    def test_generate_reply_with_mocked_gemini_success(self, mock_post):
        """generate_chatbot_reply should parse and return Gemini API text when 200 OK."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'Here is how to create a campaign on CrowdFund Egypt...'}]
                }
            }]
        }
        mock_post.return_value = mock_response

        with self.settings(GEMINI_API_KEY='valid-test-key'):
            reply = generate_chatbot_reply('How do I start a project?')
            self.assertIn('Here is how to create a campaign', reply)

    @patch('core.chatbot_engine.requests.post')
    def test_generate_reply_fallback_when_gemini_fails(self, mock_post):
        """generate_chatbot_reply should gracefully fall back to local engine if Gemini returns 500."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_post.return_value = mock_response

        with self.settings(GEMINI_API_KEY='valid-test-key'):
            reply = generate_chatbot_reply('How to donate?')
            self.assertIn('How to Make a Donation', reply)
            self.assertIn('/projects/', reply)

