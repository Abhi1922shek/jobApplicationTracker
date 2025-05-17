# In application_tracker/job_applications/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth import login, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages

from .models import JobApplication, Company # CustomUser is fetched via get_user_model
from .forms import EmailUserCreationForm, JobApplicationForm, CompanyForm

User = get_user_model() # Get your active user model (CustomUser)

# --- Authentication Views ---
def signup_view(request):
    if request.user.is_authenticated:
        return redirect('job_applications:application_list') # Redirect if already logged in

    if request.method == 'POST':
        form = EmailUserCreationForm(request.POST)
        if form.is_valid():
            # 1. Get the user object from the form's save method, but DON'T commit to DB yet.
            user = form.save(commit=False)

            # 2. CRITICAL: Set the user as INACTIVE for email confirmation.
            user.is_active = False

            # 3. Now save the user to the database. They exist but cannot log in.
            user.save()

            # 4. Prepare and send confirmation email
            current_site = get_current_site(request)
            mail_subject = 'Activate Your Job Application Tracker Account'
            
            # Generate activation token and link components
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # Reverse the URL for the activation link
            # Ensure 'activate_account' is a named URL pattern in job_applications.urls
            # and that 'job_applications' is the app_name for that urls.py
            activation_path = reverse('job_applications:activate_account', kwargs={'uidb64': uid, 'token': token})
            
            # Construct the full activation URL
            protocol = 'https' if request.is_secure() else 'http'
            activation_url = f"{protocol}://{current_site.domain}{activation_path}"

            # Debug print to check the generated URL (remove in production)
            print(f"DEBUG SIGNUP: Activation URL generated: {activation_url}")

            message_context = {
                'user': user, # Pass the user object (user.email can be used in email template)
                'activation_url': activation_url, # Pass the full URL to the email template
            }
            # Render the email body from an HTML template
            message_html = render_to_string('registration/account_activation_email.html', message_context)
            
            try:
                send_mail(
                    subject=mail_subject,
                    message='', # Plain text message (optional if sending HTML)
                    from_email='noreply@yourapplicationtracker.com', # Your "from" address
                    recipient_list=[user.email],
                    html_message=message_html # HTML version of the email
                )
                messages.info(request, f'Registration successful! An activation link has been sent to {user.email}. Please check your email to complete registration.')
                return render(request, 'registration/account_activation_sent.html', {'email': user.email})
            except Exception as e:
                # Log the detailed error to your server console/logs
                print(f"ERROR sending activation email to {user.email}: {e}")
                
                # Provide a user-friendly error message
                messages.error(request, 'We encountered an issue sending the activation email. Your registration has been recorded. Please contact support if you do not receive the email shortly.')
                # Still redirect to the "activation sent" page, but it will now show the error message
                return render(request, 'registration/account_activation_sent.html', {'email': user.email, 'email_error': True})
    else: # GET request
        form = EmailUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def activate_account_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if user.is_active:
            messages.info(request, 'Your account is already active. You can log in.')
        else:
            # 5. **CRITICAL:** Set the user as ACTIVE now.
            user.is_active = True
            user.save()
            messages.success(request, 'Thank you! Your account has been activated. You can now log in.')
            # Optionally, log the user in directly after activation:
            # login(request, user)
            # return redirect('job_applications:application_list') # Or wherever you want them to go
        return render(request, 'registration/account_activation_complete.html')
    else:
        messages.error(request, 'The activation link is invalid or has expired.')
        return render(request, 'registration/account_activation_invalid.html')


# --- Job Application CRUD Views ---
# (These remain the same as previously provided)
class ApplicationListView(LoginRequiredMixin, ListView):
    model = JobApplication
    template_name = 'job_applications/application_list.html'
    context_object_name = 'applications'
    paginate_by = 10
    def get_queryset(self):
        return JobApplication.objects.filter(user=self.request.user).select_related('company').order_by('-applied_date', '-updated_at')

class ApplicationDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = JobApplication
    template_name = 'job_applications/application_detail.html'
    context_object_name = 'application'
    def test_func(self):
        application = self.get_object()
        return self.request.user == application.user

class ApplicationCreateView(LoginRequiredMixin, CreateView):
    model = JobApplication
    form_class = JobApplicationForm
    template_name = 'job_applications/application_form.html'
    success_url = reverse_lazy('job_applications:application_list')
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    def form_valid(self, form):
        form.instance.user = self.request.user
        company_obj_from_dropdown = form.cleaned_data.get('company')
        company_name_manual = form.cleaned_data.get('company_name_manual')
        if not company_obj_from_dropdown and company_name_manual:
            company, created = Company.objects.get_or_create(user=self.request.user, name=company_name_manual.strip())
            form.instance.company = company
        elif company_obj_from_dropdown:
            form.instance.company = company_obj_from_dropdown
        return super().form_valid(form)

class ApplicationUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JobApplication
    form_class = JobApplicationForm
    template_name = 'job_applications/application_form.html'
    success_url = reverse_lazy('job_applications:application_list')
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    def test_func(self):
        application = self.get_object()
        return self.request.user == application.user
    def form_valid(self, form):
        company_obj_from_dropdown = form.cleaned_data.get('company')
        company_name_manual = form.cleaned_data.get('company_name_manual')
        if not company_obj_from_dropdown and company_name_manual:
            company, created = Company.objects.get_or_create(user=self.request.user, name=company_name_manual.strip())
            form.instance.company = company
        elif company_obj_from_dropdown:
            form.instance.company = company_obj_from_dropdown
        else:
            form.instance.company = None
        return super().form_valid(form)

class ApplicationDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = JobApplication
    template_name = 'job_applications/application_confirm_delete.html'
    success_url = reverse_lazy('job_applications:application_list')
    context_object_name = 'application'
    def test_func(self):
        application = self.get_object()
        return self.request.user == application.user

# --- Company CRUD Views ---
class CompanyListView(LoginRequiredMixin, ListView):
    model = Company
    template_name = 'job_applications/company_list.html'
    context_object_name = 'companies'
    paginate_by = 10
    def get_queryset(self):
        return Company.objects.filter(user=self.request.user).order_by('name')

class CompanyCreateView(LoginRequiredMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'job_applications/company_form.html'
    success_url = reverse_lazy('job_applications:company_list')
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class CompanyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'job_applications/company_form.html'
    success_url = reverse_lazy('job_applications:company_list')
    def test_func(self):
        company = self.get_object()
        return self.request.user == company.user

class CompanyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Company
    template_name = 'job_applications/company_confirm_delete.html'
    success_url = reverse_lazy('job_applications:company_list')
    context_object_name = 'company'
    def test_func(self):
        company = self.get_object()
        return self.request.user == company.user