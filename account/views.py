from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import is_safe_url
from account.forms import AccountAuthenticationForm, AccountUpdateForm, RegistrationForm
from account.models import Account


def home(request):
    return render(request, 'home.html')


def login_view(request, *args, **kwargs):
    # Get 'next' parameter from the request for both GET and POST
    next_url = request.POST.get('next') or request.GET.get('next')

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username').lower()  # Assume username case-insensitivity
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.info(request, f"You are now logged in as {user}.")
                if next_url and is_safe_url(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                else:
                    print(f"Unsafe or missing next URL: {next_url}")
                    return redirect("home")
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, "account/login.html", {"login_form": form, "next": next_url})


def get_redirect_if_exists(request):
    redirect = None
    if request.GET:
        if request.GET.get("next"):
            redirect = str(request.GET.get("next"))
    return redirect


def get_lower(username):
    lower_case = username.lower
    return lower_case


def logout_view(request):
    logout(request)
    return render(request, 'home.html')


@login_required(login_url='login')
def account(request, *args, **kwargs):
    context = {}
    user_id = kwargs.get("user_id")
    try:
        account = Account.objects.get(pk=user_id)
    except:
        return HttpResponse("Something went wrong.")
    if account:
        context['id'] = account.id
        context['username'] = account.username
        context['email'] = account.email
        context['hide_email'] = account.hide_email

        return render(request, "account/account.html", context)


def edit_account_view(request, *args, **kwargs):
    if not request.user.is_authenticated:
        return redirect("login")
    user_id = kwargs.get("user_id")
    account = Account.objects.get(pk=user_id)
    if account.pk != request.user.pk:
        return HttpResponse("You cannot edit someone elses profile.")
    context = {}
    if request.POST:
        form = AccountUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("account:view", user_id=account.pk)
        else:
            form = AccountUpdateForm(request.POST, instance=request.user,
                                     initial={
                                         "id": account.pk,
                                         "email": account.email,
                                         "username": account.username,
                                         "profile_image": account.profile_image,
                                         "hide_email": account.hide_email,
                                     }
                                     )
            context['form'] = form
    else:
        form = AccountUpdateForm(
            initial={
                "id": account.pk,
                "email": account.email,
                "username": account.username,
                "hide_email": account.hide_email,
            }
        )
        context['form'] = form
    return render(request, "account/edit_account.html", context)


def register_view(request, *args, **kwargs):
    user = request.user
    if user.is_authenticated:
        return HttpResponse("You are already authenticated as " + str(user.email))

    context = {}
    if request.POST:
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/login')
        else:
            context['registration_form'] = form

    else:
        form = RegistrationForm()
        context['registration_form'] = form
    return render(request, 'account/register.html', context)


def service(request):
    return render(request, 'service.html')


def custom_404(request, exception):
    return render(request, 'error_templates/404.html', status=404)


def custom_500(request):
    return render(request, 'error_templates/500.html', status=500)


def custom_403(request, exception):
    return render(request, 'error_templates/403.html', status=403)


def custom_400(request, exception):
    return render(request, 'error_templates/400.html', status=400)
