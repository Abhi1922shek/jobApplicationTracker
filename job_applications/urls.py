from django.urls import path
from . import views # Import views from the current app

# This app_name variable helps Django distinguish URL names between different apps
app_name = 'job_applications'

urlpatterns = [
    # Job Application URLs
    path('', views.ApplicationListView.as_view(), name='application_list'),
    path('application/new/', views.ApplicationCreateView.as_view(), name='application_create'),
    path('application/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('application/<int:pk>/edit/', views.ApplicationUpdateView.as_view(), name='application_update'),
    path('application/<int:pk>/delete/', views.ApplicationDeleteView.as_view(), name='application_delete'),

    # Company URLs
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('company/new/', views.CompanyCreateView.as_view(), name='company_create'),
    path('company/<int:pk>/edit/', views.CompanyUpdateView.as_view(), name='company_update'),
    path('company/<int:pk>/delete/', views.CompanyDeleteView.as_view(), name='company_delete'),
    # We don't have a CompanyDetailView defined, but you could add one if needed:
    # path('company/<int:pk>/', views.CompanyDetailView.as_view(), name='company_detail'),

    # Email activation
    path('activate/<slug:uidb64>/<slug:token>/', views.activate_account_view, name='activate_account'),
]