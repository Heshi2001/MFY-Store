from django import forms
from .models import Contact, Review, Address  # Make sure this is your model
from django.contrib.auth.models import User

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'subject', 'message']

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class AddressForm(forms.ModelForm):
    use_as_shipping = forms.BooleanField(required=False, initial=True)
    use_as_billing  = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = Address
        fields = [
            "first_name", "last_name", "phone",
            "address_line1", "address_line2",
            "city", "state", "country",
            "postal_code", "address_type", "is_default",
            "use_as_shipping", "use_as_billing",
        ]
        widgets = {
            "first_name":    forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
            "last_name":     forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
            "phone":         forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone"}),
            "address_line1": forms.TextInput(attrs={"class": "form-control", "placeholder": "Address Line 1"}),
            "address_line2": forms.TextInput(attrs={"class": "form-control", "placeholder": "Address Line 2"}),
            "city":          forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}),
            "state":         forms.TextInput(attrs={"class": "form-control", "placeholder": "State"}),
            "country":       forms.HiddenInput(),
            "postal_code":   forms.TextInput(attrs={"class": "form-control", "placeholder": "Postal Code"}),
            "address_type":  forms.HiddenInput(),
            "is_default":    forms.HiddenInput(),
        }