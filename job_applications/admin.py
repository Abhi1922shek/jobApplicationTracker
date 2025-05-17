from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm # For custom user admin forms
from .models import CustomUser, Company, JobApplication

# --- CustomUser Admin ---
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'first_name', 'last_name') # Adjust as needed for creation

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions') # Adjust as needed for change

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm # Form for changing an existing user
    add_form = CustomUserCreationForm # Form for adding a new user

    # list_display, list_filter, search_fields, ordering will be inherited from BaseUserAdmin
    # but we can override them if 'username' was heavily used there.
    # Since USERNAME_FIELD = 'email', BaseUserAdmin should adapt mostly.
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    # Fieldsets for the user change page (editing an existing user)
    # We need to make sure 'username' is not here.
    # BaseUserAdmin.fieldsets references 'username'. We must override.
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 
                                     'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fieldsets for the user creation page (adding a new user)
    # BaseUserAdmin.add_fieldsets also references 'username'. We override.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            # Ensure 'password2' is here for confirmation
            'fields': ('email', 'first_name', 'last_name', 'password', 'password2'),
        }),
    )
    # filter_horizontal is good for many-to-many fields like groups and user_permissions
    filter_horizontal = ('groups', 'user_permissions',)


# --- Company Admin ---
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'user_email_display')
    search_fields = ('name', 'website', 'user__email')
    list_filter = ('user__email',) # Or simply 'user' if you want to filter by user ID

    def user_email_display(self, obj):
        return obj.user.email
    user_email_display.short_description = 'User (Email)'
    user_email_display.admin_order_field = 'user__email' # Allows sorting by email

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.pk: # If new object
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            if not request.user.is_superuser:
                # Non-superusers can only associate companies with themselves
                kwargs["queryset"] = CustomUser.objects.filter(pk=request.user.pk)
                kwargs["initial"] = request.user.pk # Pre-select current user
                kwargs["disabled"] = True # Make the field read-only for non-superusers
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# --- JobApplication Admin ---
@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'job_title', 'get_company_name', 'user_email_display', 
        'application_source', 'applied_date', 'status', 
        'resume_submitted_link', 'resume_match_score' # Added score to list
    )
    list_filter = ('status', 'applied_date', 'user__email', 'company__name', 'application_source')
    search_fields = (
        'job_title', 'company__name', 'company_name_manual', 
        'job_description', 'notes', 'application_source', 'user__email'
    )
    readonly_fields = ('created_at', 'updated_at', 'last_reminder_sent_date', 'resume_match_score_display') # Changed here
    
    fieldsets = (
        (None, {
            'fields': ('user', 'job_title', ('company', 'company_name_manual'), 
                       'application_link', 'application_source')
        }),
        ('Application Details', {
            'fields': ('job_description', 'applied_date', 'status', 
                       'resume_submitted', 'notes')
        }),
        ('Internal Tracking', { # Removed (Read-only) from title as score is now editable via a button if needed
            'fields': ('resume_match_score_display', 'last_reminder_sent_date', 
                       'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def resume_match_score_display(self, obj):
        if obj.resume_match_score is not None:
            return f"{obj.resume_match_score:.2f}%"
        return "N/A"
    resume_match_score_display.short_description = "Resume Match Score"
    resume_match_score_display.admin_order_field = 'resume_match_score'

    def resume_submitted_link(self, obj):
        from django.utils.html import format_html
        if obj.resume_submitted:
            return format_html("<a href='{url}' target='_blank'>View/Download</a>", url=obj.resume_submitted.url)
        return "No resume"
    resume_submitted_link.short_description = "Resume"

    def user_email_display(self, obj):
        return obj.user.email
    user_email_display.short_description = 'User (Email)'
    user_email_display.admin_order_field = 'user__email'


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company":
            if not request.user.is_superuser:
                kwargs["queryset"] = Company.objects.filter(user=request.user)
        elif db_field.name == "user":
            if not request.user.is_superuser:
                kwargs["queryset"] = CustomUser.objects.filter(pk=request.user.pk)
                kwargs["initial"] = request.user.pk
                kwargs["disabled"] = True # Make the user field read-only for non-superusers
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        # Assign current user if object is new AND user field is not already set
        # (e.g., superuser might be creating an application for another user)
        if not obj.pk and not form.cleaned_data.get('user'):
            obj.user = request.user
        elif not obj.pk and form.cleaned_data.get('user'): # User explicitly set in form by superuser
            obj.user = form.cleaned_data.get('user')
        # If obj.user is not set by now, it means it's an existing object or form didn't provide it,
        # so we don't change it unless explicitly done by a superuser in the form.
        
        # Smart company handling using the application's assigned user (obj.user)
        # This ensures if a superuser creates an app for User_A, the auto-created company
        # also belongs to User_A.
        applicant_user = obj.user if obj.user else request.user # Fallback to request.user if obj.user not set

        company_obj_from_dropdown = form.cleaned_data.get('company')
        company_name_manual = form.cleaned_data.get('company_name_manual')
        if not company_obj_from_dropdown and company_name_manual:
            resolved_company, created = Company.objects.get_or_create(
                user=applicant_user, 
                name=company_name_manual.strip()
            )
            obj.company = resolved_company
        
        super().save_model(request, obj, form, change)