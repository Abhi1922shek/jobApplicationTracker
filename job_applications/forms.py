# In application_tracker/job_applications/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm # For CustomUserCreationForm
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML

from .models import JobApplication, Company # Import these models for their forms

User = get_user_model() # This will be your job_applications.CustomUser

# --- AUTHENTICATION FORMS ---

# Option 1: Adapting UserCreationForm (might still have 'username' field issues if not careful with CustomUser)
class CustomUserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("email",) # Assuming email is the USERNAME_FIELD and only field needed for ID
        # If 'username' field from AbstractUser is causing issues, this Meta might need more
        # or you should use EmailUserCreationForm below.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.form_tag = False # Template has <form>

        # This layout assumes UserCreationForm correctly uses 'email' field when USERNAME_FIELD is 'email'
        self.helper.layout = Layout(
            Field('email', css_class="mb-3", help_text=""), # Ensure this field exists on the form
            Field('password1', css_class="mb-3", label="Password", help_text=""),
            Field('password2', css_class="mb-3", label="Confirm Password", help_text="")
        )

# Option 2: More Robust Email Creation Form (Recommended)
class EmailUserCreationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput, help_text="")
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput, help_text="")

    class Meta:
        model = User # Uses your CustomUser model
        fields = ('email',)
        # If your CustomUser model has other required fields like first_name, add them here:
        # fields = ('email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Explicitly remove model-based help_text if any, as we want none initially
        if 'email' in self.fields:
             self.fields['email'].help_text = ""

        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field('email', css_class="mb-3"),
            Field('password', css_class="mb-3"),
            Field('password2', css_class="mb-3")
        )

    def clean_password2(self):
        cd = self.cleaned_data
        password = cd.get('password')
        password2 = cd.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match.")
        # You might want to add Django's password validators here if ModelForm doesn't pick them up
        # from the User model automatically for the 'password' field.
        # from django.contrib.auth.password_validation import validate_password
        # if password:
        #     try:
        #         validate_password(password, self.instance)
        #     except forms.ValidationError as e:
        #         self.add_error('password', e) # Add errors to the 'password' field
        return password2 # Return password2, not cd.get('password2') to avoid issues if it's None initially

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# --- JOB APPLICATION AND COMPANY FORMS ---

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Google, Microsoft'}),
            'website': forms.URLInput(attrs={'placeholder': 'e.g., https://careers.google.com'}),
        }
        # No help_text override needed if model's help_text is fine or you want none.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.form_tag = False # Template will have <form> tags
        # If you want crispy to render a submit button:
        # self.helper.add_input(Submit('submit', 'Save Company', css_class='btn-primary'))
        # Or define a full layout:
        self.helper.layout = Layout(
            Field('name', css_class="mb-3"),
            Field('website', css_class="mb-3")
        )


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = [
            'company', 'company_name_manual', 'job_title', 'job_description',
            'application_link', 'application_source',
            'applied_date', 'status', 'resume_submitted', 'notes'
        ]
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}), # Basic Bootstrap class
            'company_name_manual': forms.TextInput(attrs={'placeholder': 'If company not in list above'}),
            'job_title': forms.TextInput(attrs={'placeholder': 'e.g., Software Engineer Intern'}),
            'job_description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Paste job description here...'}),
            'application_link': forms.URLInput(attrs={'placeholder': 'e.g., https://example.com/job/123'}),
            'application_source': forms.Select(), # Default widget is fine, crispy will style
            'applied_date': forms.DateInput(attrs={'type': 'date'}),
            'status': forms.Select(),
            'resume_submitted': forms.FileInput(),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any notes, contacts, interview details...'}),
        }
        # Remove default help texts if you want none initially
        # You can do this field by field or by iterating in __init__
        help_texts = {field: '' for field in fields} # Clears all help texts

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('user', None) # Get user passed from view
        super().__init__(*args, **kwargs)

        # Clear all default help texts if not done via Meta.help_texts
        for field_name in self.fields:
            self.fields[field_name].help_text = ''

        if current_user:
            self.fields['company'].queryset = Company.objects.filter(user=current_user).order_by('name')

        self.fields['company'].required = False
        if 'application_source' in self.fields and self.Meta.model._meta.get_field('application_source').blank:
            self.fields['application_source'].required = False

        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.form_tag = False # Template has <form> tags
        # Define a layout for crispy-forms if you want more control than just {{ form|crispy }}
        # For now, letting {{ form|crispy }} handle it with default field rendering is fine.
        # Example of a simple layout for all fields:
        # self.helper.layout = Layout(*self.fields.keys()) # Render all fields in order

    def clean(self):
        cleaned_data = super().clean()
        company = cleaned_data.get('company')
        company_name_manual = cleaned_data.get('company_name_manual')

        if not company and not company_name_manual:
            self.add_error(None, "Please select an existing company or enter a new company name.")
        if company and company_name_manual:
            self.add_error('company_name_manual', "Please do not enter a manual company name if you have selected a company from the list.")
        return cleaned_data