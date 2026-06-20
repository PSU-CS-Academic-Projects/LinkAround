"""
URL configuration for LinkAround_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from LinkAround_main import views as main_views

urlpatterns = [
    path('', main_views.home, name='home'),
    path('admin-dashboard/', main_views.admin_dashboard, name='admin_dashboard'),
    path('seeker/register/', main_views.seeker_register, name='seeker_register'),
    path('employer/register/', main_views.employer_register, name='employer_register'),
    path('accounts/register/', main_views.account_register, name='account_register'),
    path('accounts/login/', main_views.login_view, name='login'),
    path('accounts/logout/', main_views.logout_view, name='logout'),
    path('accounts/choose-role/', main_views.choose_role, name='choose_role'),
    path('accounts/google/login/', main_views.social_provider_login, {'provider': 'google'}, name='social_google_login'),
    path('accounts/microsoft/login/', main_views.social_provider_login, {'provider': 'microsoft'}, name='social_microsoft_login'),
    path('accounts/apple/login/', main_views.social_provider_login, {'provider': 'apple'}, name='social_apple_login'),
    path('oauth/', include('allauth.urls')),
    path('seeker/edit/', main_views.seeker_edit, name='seeker_edit'),
    path('employer/edit/', main_views.employer_edit, name='employer_edit'),
    path('seekers/', main_views.seeker_list, name='seeker_list'),
    path(
        'portfolio/<int:seeker_id>/file/',
        main_views.portfolio_file,
        name='portfolio_file',
    ),
    path(
        'shortlist/<int:seeker_id>/add/',
        main_views.add_to_shortlist,
        name='add_to_shortlist',
    ),
    path(
        'employer/<int:employer_id>/dashboard/',
        main_views.employer_dashboard,
        name='employer_dashboard',
    ),
    path(
        'employer/<int:employer_id>/covered-fields/',
        main_views.employer_covered_fields,
        name='employer_covered_fields',
    ),
    path(
        'employer/<int:employer_id>/folders/create/',
        main_views.create_folder,
        name='create_folder',
    ),
    path(
        'folders/<int:folder_id>/rename/',
        main_views.rename_folder,
        name='rename_folder',
    ),
    path(
        'folders/<int:folder_id>/delete/',
        main_views.delete_folder,
        name='delete_folder',
    ),
    path(
        'shortlist/<int:shortlist_id>/move/',
        main_views.move_to_folder,
        name='move_to_folder',
    ),
    path(
        'seeker/<int:seeker_id>/notifications/',
        main_views.seeker_notifications,
        name='seeker_notifications',
    ),
    path(
        'notification/<int:notification_id>/read/',
        main_views.mark_notification_read,
        name='mark_notification_read',
    ),
    path('admin/', admin.site.urls),
]
