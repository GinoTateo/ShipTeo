# your_app/decorators.py
from django.http import HttpResponseForbidden
from functools import wraps

from django.shortcuts import render


def user_is_rsr(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_rsr():
            return function(request, *args, **kwargs)
        else:
            context = {
                'message': "You do not have permission to access this page."
            }
            return render(request, "error_templates/forbidden.html", context, status=403)

    return wrap


def user_is_warehouse_manager(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_warehouse_manager():
            return function(request, *args, **kwargs)
        else:
            context = {
                'message': "You do not have permission to access this page."
            }
            return render(request, "error_templates/forbidden.html", context, status=403)

    return wrap


def user_is_regional_manager(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_regional_manager():
            return function(request, *args, **kwargs)
        else:
            context = {
                'message': "You do not have permission to access this page."
            }
            return render(request, "error_templates/forbidden.html", context, status=403)

    return wrap


def user_is_division_manager(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_division_manager():
            return function(request, *args, **kwargs)
        else:
            context = {
                'message': "You do not have permission to access this page."
            }
            return render(request, "error_templates/forbidden.html", context, status=403)

    return wrap


def user_is_warehouse_worker(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_warehouse_worker():
            return function(request, *args, **kwargs)
        else:
            context = {
                'message': "You do not have permission to access this page."
            }
            return render(request, "error_templates/forbidden.html", context, status=403)

    return wrap
