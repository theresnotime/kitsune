import inspect
from functools import wraps

from django.apps import apps
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.db.models import Model
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.http import urlquote

from kitsune.access import utils as access
from kitsune.sumo.urlresolvers import reverse


def user_access_decorator(
    redirect_func, redirect_url_func, deny_func=None, redirect_field=REDIRECT_FIELD_NAME
):
    """
    Helper function that returns a decorator.

    * redirect func ----- If truthy, a redirect will occur
    * deny_func --------- If truthy, HttpResponseForbidden is returned.
    * redirect_url_func - Evaluated at view time, returns the redirect URL
                          i.e. where to go if redirect_func is truthy.
    * redirect_field ---- What field to set in the url, defaults to Django's.
                          Set this to None to exclude it from the URL.

    """

    def decorator(view_fn):
        def _wrapped_view(request, *args, **kwargs):
            redirect = redirect_func(request.user)
            if redirect and not request.is_ajax():
                # We must call reverse at the view level, else the threadlocal
                # locale prefixing doesn't take effect.
                redirect_url = redirect_url_func() or reverse("users.login")

                # Redirect back here afterwards?
                if redirect_field:
                    path = urlquote(request.get_full_path())
                    redirect_url = "%s?%s=%s" % (redirect_url, redirect_field, path)

                return HttpResponseRedirect(redirect_url)
            elif (redirect and request.is_ajax()) or (deny_func and deny_func(request.user)):
                return HttpResponseForbidden()

            return view_fn(request, *args, **kwargs)

        return wraps(view_fn)(_wrapped_view)

    return decorator


def logout_required(redirect):
    """Requires that the user *not* be logged in."""

    def redirect_func(user):
        return user.is_authenticated

    if hasattr(redirect, "__call__"):
        return user_access_decorator(
            redirect_func, redirect_field=None, redirect_url_func=lambda: reverse("home")
        )(redirect)
    else:
        return user_access_decorator(
            redirect_func, redirect_field=None, redirect_url_func=lambda: redirect
        )


def login_required(func, login_url=None, redirect=REDIRECT_FIELD_NAME, only_active=True):
    """Requires that the user is logged in."""
    if only_active:

        def redirect_func(user):
            return not (user.is_authenticated and user.is_active)

    else:

        def redirect_func(user):
            return not user.is_authenticated

    return user_access_decorator(
        redirect_func, redirect_field=redirect, redirect_url_func=lambda: login_url
    )(func)


def permission_required(perm, login_url=None, redirect=REDIRECT_FIELD_NAME, only_active=True):
    """A replacement for django.contrib.auth.decorators.permission_required
    that doesn't ask authenticated users to log in."""
    if only_active:

        def deny_func(user):
            return not (user.is_active and user.has_perm(perm))

    else:

        def deny_func(user):
            return not user.has_perm(perm)

    return user_access_decorator(
        lambda u: not u.is_authenticated,
        redirect_field=redirect,
        redirect_url_func=lambda: login_url,
        deny_func=deny_func,
    )


def has_perm_or_owns_or_403(perm, owner_attr, obj_lookup, perm_obj_lookup, **kwargs):
    """Act like permission_required_or_403 but also grant permission to owners.

    Arguments:
        perm: authority permission to check, e.g. 'forums_forum.edit_forum'

        owner_attr: Attr of model object that references the owner

        obj_lookup: Triple that specifies a lookup to the object on which
            ownership should be compared. Items in the tuple are...
            (model class or import path thereof,
             kwarg name specifying field and comparator (e.g. 'id__exact'),
             name of kwarg containing the value to which to compare)

        perm_obj_lookup: Triple that specifies a lookup to the object on which
            to check for permission. Elements of the tuple are as in
            obj_lookup.

    """

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # based on authority/decorators.py
            user = request.user
            if user.is_authenticated:
                obj = _resolve_lookup(obj_lookup, kwargs)
                perm_obj = _resolve_lookup(perm_obj_lookup, kwargs)
                granted = access.has_perm_or_owns(user, perm, obj, perm_obj, owner_attr)
                if granted or user.has_perm(perm):
                    return view_func(request, *args, **kwargs)

            # In all other cases, permission denied
            return HttpResponseForbidden()

        return wraps(view_func)(_wrapped_view)

    return decorator


def _resolve_lookup(obj_lookup, view_kwargs):
    """Return the object indicated by the lookup triple and the kwargs passed
    to the view.

    """
    (model, lookup, arg_name) = obj_lookup
    value = view_kwargs.get(arg_name)
    if value is None:
        raise ValueError("Expected kwarg '%s' not found." % arg_name)
    if isinstance(model, str):
        model_class = apps.get_model(*model.split("."))
    else:
        model_class = model
    if model_class is None:
        raise ValueError("The given argument '%s' is not a valid model." % model)
    if inspect.isclass(model_class) and not issubclass(model_class, Model):
        raise ValueError("The argument '%s' needs to be a model." % model)
    return get_object_or_404(model_class, **{lookup: value})
