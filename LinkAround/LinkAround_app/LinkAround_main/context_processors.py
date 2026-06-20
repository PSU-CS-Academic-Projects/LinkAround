from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q

from .models import FieldPreference, RecentActivity, SeekerNotification
from .rbac import (
    ROLE_ADMIN,
    ROLE_EMPLOYER,
    ROLE_SEEKER,
    can_act_as_employer,
    can_act_as_seeker,
    get_primary_role,
    is_admin_user,
    user_has_any_primary_role,
)


def _profile(user, attribute):
    try:
        return getattr(user, attribute)
    except (AttributeError, ObjectDoesNotExist):
        return None


def role_context(request):
    user = request.user
    can_use_django_admin = (
        user.is_authenticated
        and user.is_active
        and user.is_staff
    )
    trending_fields = FieldPreference.objects.annotate(
        public_seekers=Count(
            'seeker_pool',
            filter=Q(seeker_pool__is_public=True),
            distinct=True,
        ),
    ).order_by('-public_seekers', 'name')[:5]
    if not user.is_authenticated:
        return {
            'is_seeker': False,
            'is_employer': False,
            'is_admin': False,
            'can_act_as_seeker': False,
            'can_act_as_employer': False,
            'can_use_django_admin': False,
            'needs_role': False,
            'primary_role': None,
            'seeker_profile': None,
            'employer_profile': None,
            'has_seeker_profile': False,
            'has_employer_profile': False,
            'unread_notification_count': 0,
            'recent_activities': [],
            'trending_fields': trending_fields,
        }

    primary_role = get_primary_role(user)
    activity_role = ROLE_ADMIN if is_admin_user(user) else primary_role
    seeker_profile = _profile(user, 'seeker_profile')
    employer_profile = _profile(user, 'employer_profile')
    unread_count = 0
    if seeker_profile:
        unread_count = SeekerNotification.objects.filter(
            seeker=seeker_profile,
            is_read=False,
        ).count()

    return {
        'is_seeker': primary_role == ROLE_SEEKER,
        'is_employer': primary_role == ROLE_EMPLOYER,
        'is_admin': is_admin_user(user),
        'can_act_as_seeker': can_act_as_seeker(user),
        'can_act_as_employer': can_act_as_employer(user),
        'can_use_django_admin': can_use_django_admin,
        'needs_role': not user_has_any_primary_role(user) and not is_admin_user(user),
        'primary_role': primary_role,
        'seeker_profile': seeker_profile,
        'employer_profile': employer_profile,
        'has_seeker_profile': seeker_profile is not None,
        'has_employer_profile': employer_profile is not None,
        'unread_notification_count': unread_count,
        'recent_activities': RecentActivity.objects.filter(
            user=user,
            role=activity_role,
        )[:5] if activity_role else [],
        'trending_fields': trending_fields,
    }
