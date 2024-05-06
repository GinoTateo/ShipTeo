from django.test import TestCase
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User


class CaseInsensitiveAuthTests(TestCase):
    def setUp(self):
        # Create a test user
        User = get_user_model()
        self.user = User.objects.create_user('testUser', 'test@example.com', 'testpassword123')

    def test_login_case_insensitive(self):
        # Test logging in with different cases
        response = self.client.login(username='TESTUSER', password='testpassword123')
        self.assertTrue(response)  # Assert login successful with uppercase username

        response = self.client.login(username='testuser', password='testpassword123')
        self.assertTrue(response)  # Assert login successful with lowercase username

        response = self.client.login(username='TestUser', password='testpassword123')
        self.assertTrue(response)  # Assert login successful with original case

    def test_incorrect_password(self):
        # Ensure that incorrect password fails
        response = self.client.login(username='testUser', password='wrongpassword')
        self.assertFalse(response)

    def test_nonexistent_user(self):
        # Test logging in with a username that does not exist
        response = self.client.login(username='nobody', password='testpassword123')
        self.assertFalse(response)
