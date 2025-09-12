from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.first_name = form.cleaned_data.get("first_name", "") or user.first_name
        user.last_name = form.cleaned_data.get("last_name", "") or user.last_name
        if commit:
            user.save()
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.email = data.get("email", "") or user.email
        user.first_name = data.get("given_name", "") or data.get("first_name", "") or user.first_name
        user.last_name = data.get("family_name", "") or data.get("last_name", "") or user.last_name
        return user
