from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, AdminProfile, OrdinaryUserProfile


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    user_type = forms.ChoiceField(choices=User.USER_TYPE_CHOICES, initial='ordinary')

    class Meta:
        model = User
        fields = ('username', 'email', 'user_type', 'password1', 'password2')


class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = AdminProfile
        fields = ('department', 'phone', 'permissions_level', 'access_code')


class OrdinaryUserProfileForm(forms.ModelForm):
    class Meta:
        model = OrdinaryUserProfile
        fields = ('bio', 'avatar', 'birth_date', 'phone', 'city', 'subscription_active')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }
