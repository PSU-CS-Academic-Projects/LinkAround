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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from LinkAround_main import views as main_views

urlpatterns = [
    path('', main_views.home, name='home'),
    path('seeker/register/', main_views.seeker_register, name='seeker_register'),
    path('employer/register/', main_views.employer_register, name='employer_register'),
    path('seekers/', main_views.seeker_list, name='seeker_list'),
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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
