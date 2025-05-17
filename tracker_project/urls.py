from django.contrib import admin
from django.urls import path, include # Add include
from django.contrib.auth import views as auth_views # For Django's built-in auth views
from job_applications import views as job_app_views # Import your app's views for signup

# For serving media files during development (resume uploads)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication URLs
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'), # Provide template for logout too
    path('accounts/signup/', job_app_views.signup_view, name='signup'), # Your custom signup view

    # Password Reset URLs (Optional, but good to have)
    # You'll need to create templates for these if you enable them.
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # Include URLs from the job_applications app
    # All URLs from job_applications.urls will be prefixed with '' (i.e., at the root)
    # If you wanted them prefixed, e.g., /tracker/, you'd use path('tracker/', include(...))
    path('', include('job_applications.urls')),
]

# This is only for development to serve media files (like resumes)
# In production, your web server (e.g., Nginx) should be configured to serve media files.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)