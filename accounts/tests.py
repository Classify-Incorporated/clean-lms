
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount, SocialToken
from allauth.socialaccount.signals import pre_social_login
from .adapter import CustomSocialAccountAdapter, MicrosoftAuth2Adapter
from .models import Profile
from .provider import MicrosoftProvider
from allauth.socialaccount.models import SocialLogin
from django.test import RequestFactory
User = get_user_model()
from allauth.exceptions import ImmediateHttpResponse

class MicrosoftAuthTest(TestCase):
    
    def setUp(self):
        # Setup necessary test data
        self.client = Client()
        self.email = "charles@hccci.edu.ph"
        self.first_name = "CHARLES"
        self.last_name = "ALEGRE"
        self.microsoft_token = "fake_token"
        
        # Add a unique 'id' field to mimic a real Microsoft profile
        self.microsoft_profile = {
            'id': 'd25a0546-d440-4795-8549-4f913fd0d414',
            'mail': self.email,
            'givenName': self.first_name,
            'surname': self.last_name,
            'userPrincipalName': self.email
        }

        # Create the necessary user
        self.user = User.objects.create_user(
            username=self.email, 
            email=self.email, 
            first_name=self.first_name, 
            last_name=self.last_name,
            password='testpassword'
        )

    @patch('requests.get')  # Mock the Microsoft Graph API call
    def test_complete_login_creates_social_account_and_token(self, mock_get):
        # Simulate Microsoft API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.microsoft_profile
        
        # Create a request using Django's test client
        request = self.client.get(reverse('microsoft_login'))

        # Initialize the adapter with the request
        adapter = MicrosoftAuth2Adapter(request)

        token = SocialToken(token=self.microsoft_token)

        # Run the complete_login method
        social_login = adapter.complete_login(request, None, token)
        
        # Check if social_login is not None to avoid AttributeError
        if social_login is not None:
            self.assertEqual(social_login.user.email, self.email)
            self.assertEqual(social_login.user.first_name, self.first_name)
            self.assertEqual(social_login.user.last_name, self.last_name)
        else:
            self.fail("social_login is None")

        # Check if the SocialAccount is created
        social_account = SocialAccount.objects.get(user=social_login.user, provider=MicrosoftProvider.id)
        self.assertIsNotNone(social_account)
        
        # Check if the SocialToken is created and linked
        social_token = SocialToken.objects.get(account=social_account)
        self.assertEqual(social_token.token, self.microsoft_token)

    @patch('requests.get')  # Mock the Microsoft Graph API call
    def test_pre_social_login_existing_user(self, mock_get):
        # Simulate Microsoft API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self.microsoft_profile

        adapter = CustomSocialAccountAdapter()

        # Create a valid request with session
        request = RequestFactory().get(reverse('microsoft_login'))
        request.session = self.client.session  # Attach a session manually

        # Create a fake social login object
        sociallogin = SocialLogin(account=SocialAccount(user=self.user, provider=MicrosoftProvider.id))
        sociallogin.account.extra_data = self.microsoft_profile

        # Trigger the pre_social_login signal
        try:
            adapter.pre_social_login(request, sociallogin)
        except ImmediateHttpResponse as e:
            # Ensure the response redirects to the dashboard
            self.assertEqual(e.response.status_code, 302)
            self.assertIn("/dashboard/", e.response.url)

    def test_save_user_creates_profile(self):
        adapter = CustomSocialAccountAdapter()
        request = RequestFactory().get(reverse('microsoft_login'))
        request.session = self.client.session  # Manually attach session to request

        # Create a SocialLogin object with a user
        sociallogin = SocialLogin(account=SocialAccount(user=self.user, provider=MicrosoftProvider.id))

        # Ensure sociallogin.user is not None
        if not sociallogin.user:
            self.fail("sociallogin.user is None")

        # Run save_user
        adapter.save_user(request, sociallogin)

        # Check if the profile is created
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.first_name, self.first_name)
        self.assertEqual(profile.last_name, self.last_name)
