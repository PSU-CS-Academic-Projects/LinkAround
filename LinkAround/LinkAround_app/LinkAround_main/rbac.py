from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth.models import Group
from django.shortcuts import redirect
from django.urls import reverse


ROLE_SEEKER = 'Seeker'
ROLE_EMPLOYER = 'Employer'
ROLE_ADMIN = 'Admin'
PRIMARY_ROLES = (ROLE_SEEKER, ROLE_EMPLOYER)
ALL_ROLES = (ROLE_SEEKER, ROLE_EMPLOYER, ROLE_ADMIN)


def ensure_role_groups():
    for role in ALL_ROLES:
        Group.objects.get_or_create(name=role)


def assign_role(user, role_name):
    if role_name not in PRIMARY_ROLES:
        raise ValueError(f'Unsupported primary role: {role_name}')

    ensure_role_groups()
    user.groups.remove(*Group.objects.filter(name__in=PRIMARY_ROLES))
    user.groups.add(Group.objects.get(name=role_name))


def user_has_role(user, role_name):
    return user.is_authenticated and user.groups.filter(name=role_name).exists()


def is_admin_user(user):
    return (
        user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or user.groups.filter(name=ROLE_ADMIN).exists()
        )
    )


def user_has_any_primary_role(user):
    return user.is_authenticated and user.groups.filter(name__in=PRIMARY_ROLES).exists()


def user_can_access_role(user, role_name):
    return is_admin_user(user) or user_has_role(user, role_name)


def can_act_as_seeker(user):
    return user_can_access_role(user, ROLE_SEEKER)


def can_act_as_employer(user):
    return user_can_access_role(user, ROLE_EMPLOYER)


def get_primary_role(user):
    if not user.is_authenticated:
        return None
    role = user.groups.filter(name__in=PRIMARY_ROLES).values_list('name', flat=True).first()
    return role


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = reverse('login')
                return redirect_to_login(request.get_full_path(), login_url)

            if is_admin_user(request.user):
                return view_func(request, *args, **kwargs)

            if not user_has_any_primary_role(request.user) and not is_admin_user(request.user):
                messages.info(request, 'Choose your account role before continuing.')
                return redirect('choose_role')

            if any(user_has_role(request.user, role) for role in roles):
                return view_func(request, *args, **kwargs)

            messages.error(request, 'You do not have permission to access that page.')
            return redirect('home')

        return wrapped

    return decorator


seeker_required = role_required(ROLE_SEEKER)
employer_required = role_required(ROLE_EMPLOYER)
admin_required = role_required(ROLE_ADMIN)
