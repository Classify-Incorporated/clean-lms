# accounts/provider.py
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

class MicrosoftAccount(ProviderAccount):
    def get_avatar_url(self):
        return self.account.extra_data.get('picture')

    def to_str(self):
        dflt = super(MicrosoftAccount, self).to_str()
        return self.account.extra_data.get('name', dflt)

class MicrosoftProvider(OAuth2Provider):
    id = 'microsoft'
    name = 'Microsoft'
    account_class = MicrosoftAccount

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(email=data.get('mail') or data.get('userPrincipalName'),
                    first_name=data.get('givenName'),
                    last_name=data.get('surname'))

provider_classes = [MicrosoftProvider]
