from django.contrib import admin

from .models import (
    EmployerProfile,
    EmployerShortlist,
    FieldPreference,
    RecentActivity,
    Region,
    SeekerNotification,
    SeekerProfile,
    ShortlistFolder,
)


@admin.register(FieldPreference)
class FieldPreferenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'category')


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'category')


@admin.register(RecentActivity)
class RecentActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'activity_type', 'label', 'created_at')
    list_filter = ('role', 'activity_type')
    search_fields = ('user__username', 'label', 'url')
    readonly_fields = ('created_at',)


@admin.register(SeekerProfile)
class SeekerProfileAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'email',
        'user',
        'location',
        'work_arrangement',
        'is_public',
        'allow_download',
        'created_at',
    )
    list_filter = ('is_public', 'allow_download', 'degree_level', 'work_arrangement', 'location')
    search_fields = (
        'full_name',
        'email',
        'degree',
        'bio',
        'user__username',
        'preferred_fields__name',
        'location__name',
    )
    filter_horizontal = ('preferred_fields',)
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user', 'location')


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'email', 'user', 'location', 'created_at')
    list_filter = ('location', 'business_fields')
    search_fields = (
        'company_name',
        'contact_person',
        'email',
        'user__username',
        'business_fields__name',
        'location__name',
    )
    filter_horizontal = ('business_fields',)
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user', 'location')


@admin.register(EmployerShortlist)
class EmployerShortlistAdmin(admin.ModelAdmin):
    list_display = ('employer', 'seeker', 'folder', 'created_at')
    list_filter = ('folder', 'created_at')
    search_fields = (
        'employer__company_name',
        'seeker__full_name',
        'folder__name',
        'notes',
    )
    readonly_fields = ('created_at',)
    autocomplete_fields = ('employer', 'seeker', 'folder')


@admin.register(SeekerNotification)
class SeekerNotificationAdmin(admin.ModelAdmin):
    list_display = ('seeker', 'shortlist', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = (
        'seeker__full_name',
        'shortlist__employer__company_name',
        'message',
    )
    readonly_fields = ('created_at',)
    autocomplete_fields = ('seeker', 'shortlist')


@admin.register(ShortlistFolder)
class ShortlistFolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'employer', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'employer__company_name')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('employer',)
