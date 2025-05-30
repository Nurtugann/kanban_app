# main/forms.py

# main/forms.py

from django import forms
from .models import Company, CompanyStatusHistory, Comment

# main/forms.py

from django import forms
from .models import Company, Status, REGION_CHOICES

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        # включаем region в список полей
        fields = ['name', 'status', 'region']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'region': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        """
        Если user не суперпользователь —
        регион выбирается только из профиля.
        """
        super().__init__(*args, **kwargs)

        # все статусы по умолчанию
        self.fields['status'].queryset = Status.objects.order_by('order')

        if not user or not user.is_staff:
            # обычным пользователям показываем только их регион
            user_region = getattr(user.profile, 'region', None)
            self.fields['region'].choices = [
                (user_region, dict(REGION_CHOICES).get(user_region))
            ]
            # и скрываем селектор, если хотите:
            # self.fields['region'].widget = forms.HiddenInput()



class CompanyStatusHistoryForm(forms.ModelForm):
    class Meta:
        model = CompanyStatusHistory
        fields = ['status', 'changed_at']
        widgets = {
            'status':     forms.Select(attrs={'class': 'form-select'}),
            'changed_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
        }

    # если используете datetime-local, нужно подстроить формат:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.changed_at:
            self.fields['changed_at'].initial = self.instance.changed_at.strftime('%Y-%m-%dT%H:%M')

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# main/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import REGION_CHOICES

User = get_user_model()

class SignUpForm(UserCreationForm):
    region = forms.ChoiceField(
        choices=REGION_CHOICES,
        label="Регион",
        help_text="Выберите регион пользователя"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "region", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # после сохранения пользователя — сразу заполняем профиль:
            user.profile.region = self.cleaned_data["region"]
            user.profile.save()
        return user
