from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect, BadHeaderError
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.template import loader
from django.template.loader import render_to_string
from django.urls import resolve
from django.utils.html import strip_tags
from django.utils.timezone import now

from account.models import Account
from operations.models import Item
from rsr.models import Store, Route, StoreListItem
from .forms import MerchForm
from .models import Merch, Request, Docket


@login_required(login_url='login')
def index(request):
    latest_list = Merch.objects.order_by('-completeDate')[:25]
    template = loader.get_template('merch/index.html')
    context = {
        'latest_list': latest_list
    }
    return HttpResponse(template.render(context, request))


@login_required(login_url='login')
def docket(request, user_id):
    my_dockets = Docket.objects.order_by('-startDate')[:25]
    # dockets_list = my_dockets.order_by('-date')[:5]
    template = loader.get_template('merch/docket.html')
    context = {
        'list': my_dockets,
    }
    return HttpResponse(template.render(context, request))


@login_required(login_url='login')
def detail(request, merch_id):
    merch = get_object_or_404(Merch, pk=merch_id)
    return render(request, 'merch/detail.html', {'merch': merch})


@login_required(login_url='login')
def dashboard(request):
    # user = get_object_or_404(Account, username=merchuser)
    # latest_list = Merch.objects.order_by('-detail')[:5]

    template = loader.get_template('merch/merchandiser_dashboard_view.html')
    user = Account.objects.get(username=request.user)
    if (request.user.is_superuser):
        rtmd = Store.objects.all()
    else:
        rtmd = Store.objects.filter(RSRrt=user.username)

    today = datetime.today()
    if Docket.objects.filter(planDate=today).exists():
        todays_docket = Docket.objects.get(planDate=today)
        stores = todays_docket.store_list.all()
    else:
        todays_docket = None
        stores = None

    merch_request = Request.objects.filter(receiver=user, is_active=True)

    context = {
        'docket': todays_docket,
        'stores': stores,
        'route': rtmd,
        'requests': merch_request
    }
    return HttpResponse(template.render(context, request))


@login_required(login_url='login')
def route(request):
    template = loader.get_template('merch/route_view.html')
    user = Account.objects.get(username=request.user)
    if (request.user.is_superuser):
        rtmd = Store.objects.all()
    else:
        rtmd = Store.objects.filter(RSRrt=user.username)

    context = {
        'stores': rtmd,
        'requests': rtmd,
    }
    return HttpResponse(template.render(context, request))


@login_required(login_url='login')
def merchuser(request, merchuser):
    user = get_object_or_404(Account, username=merchuser)
    profile = Account.objects.get(username=user)
    url_name = resolve(request.path).url_name
    context = {
        'profile': profile,
        'url_name': url_name,
    }
    return render(request, 'merch/merchandiser_view.html', context)


@login_required(login_url='login')
def add(request):
    return render(request, 'addHome.html')


@login_required(login_url='login')
def addStore(request):
    if request.method == 'POST':
        form = StoreForm2(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/add')

    else:
        form = StoreForm2()

    return render(request,
                  'add.html',
                  {'form': form})


@login_required(login_url='login')
def addMerch(request, store_id):
    if request.method == 'POST':
        form = MerchForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/add')

    else:
        form = MerchForm()

    return render(request,
                  'add.html',
                  {'form': form})


@login_required(login_url='login')
def addWD(request):
    if request.method == 'POST':
        form = WeeklyDataForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/add')

    else:
        form = WeeklyDataForm()

    return render(request,
                  'add.html',
                  {'form': form})


@login_required(login_url='login')
def addItem(request):
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/add')

    else:
        form = ItemForm()

    return render(request,
                  'add.html',
                  {'form': form})


@login_required
def SpecificStoreMerch(request, user_id, store_id):
    user = Account.objects.get(username=request.user)
    if (request.user.is_superuser):
        rtmd = Store.objects.all()
    else:
        rtmd = Store.objects.filter(RSRrt=user.username)
        # storedisplay = Store.displays.objects.filter(RSRrt=user.username)

    routeData = get_object_or_404(rtmd, pk=store_id)
    md = Merch.objects.filter(store=routeData).order_by('-date')
    # displays = Merch.objects.filter(store=routeData)
    return render(request, 'merch/index.html', {'store': routeData,
                                                'latest_list': md,
                                                # 'display': displays
                                                })


# class OrderSummaryView(LoginRequiredMixin, View):
#     def get(self, *args, **kwargs):
#
#         try:
#             user = get_object_or_404(Account, username=self.kwargs.get('username'))
#             order = Order.objects.get(user, ordered=False)
#             context = {
#                 'object' : order
#             }
#             return render(self.request, 'order_summary.html', context)
#         except ObjectDoesNotExist:
#             messages.error(self.request, "You do not have an order")
#             return redirect("order_summary.html")

@login_required
def send_email(request):
    today = datetime.datetime.now()
    # fivedays = datetime.timedelta(days=5)
    # dayrange = today - fivedays

    enddate = today - datetime.timedelta(days=5)

    latest_list = Merch.objects.filter(date__range=[enddate, today], store__RSRrt='731')
    # latest_list.filter(date__range=[today, fivedays])

    html_message = render_to_string('email_template.html', {'latest_list': latest_list})
    plain_message = strip_tags(html_message)

    subject = request.POST.get('subject', 'Merch ')
    message = request.POST.get('message', plain_message)
    from_email = request.POST.get('from_email', 'Tateomerch@gmail.com')
    if subject and message and from_email:
        try:
            send_mail(subject, message, from_email, ['TateoGino@gmail.com'])
        except BadHeaderError:
            return HttpResponse('Invalid header found.')
        return HttpResponseRedirect('home')
    else:
        return HttpResponse('Make sure all fields are entered and valid.')


@login_required
def create_merch(request, storeid):
    current_store = get_object_or_404(Store, pk=storeid)
    current_user = request.user

    if request.method == 'POST':
        form = MerchForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/merch/dashboard')
        else:
            print(form.errors)

    else:
        form = MerchForm(initial={"user": current_user, "store": current_store})

    return render(request,
                  'create-merch.html',
                  {'form': form,
                   'store': current_store
                   })


@login_required
def merch_request(request, *args, **kwargs):
    context = {}
    user = request.user
    if user.is_authenticated:
        # user_id = kwargs.get("user_id")
        # rout = Request.objects.get(pk=user_id)
        if user:
            merch_request = Request.objects.filter(receiver=user, is_active=True)
            context['merch_requests'] = merch_request
        else:
            return HttpResponse("You cant view another users friend requests")
    else:
        redirect('Login')
    return render(request, "merch/request_view.html", context)


@login_required
def send_merch_request(request, receiver_id, store_id):
    payload = {}
    user_id = request.user.id
    if user_id:
        user = Account.objects.get(id=user_id)
        receiver = Account.objects.get(id=receiver_id)
        store = Store.objects.get(id=store_id)
        try:
            merch_request = Request.objects.filter(sender=user, receiver=receiver)
            try:
                for request in merch_request:
                    if request.is_active and request.store == store:
                        raise Exception("Already sent a request")

                merch_request = Request(sender=user, receiver=receiver, store=store)
                merch_request.save()
                payload['response'] = "Merch request sent."
            except Exception as e:
                payload['response'] = str(e)
        except Request.DoesNotExist:
            mrq = Request(sender=user, receiver=receiver, store=store)
            mrq.save()
            payload['response'] = "Merch request sent."

        if payload['response'] is None:
            payload['response'] = "Something went wrong."
    else:
        payload['response'] = "Unable to send request."

    return redirect('rsr:route-review')


@login_required
def cancel_merch_request(request, receiver_id, store_id):
    payload = {}
    user_id = request.user.id
    if user_id:
        user = Account.objects.get(id=user_id)
        receiver = Account.objects.get(id=receiver_id)
        store = Store.objects.get(id=store_id)
        merch_request = Request.objects.filter(sender=user, receiver=receiver)
        try:
            for request in merch_request:
                if request.is_active and request.store == store:
                    request.delete()
        except Exception as e:
            payload['response'] = str(e)
    else:
        payload['response'] = "Unable to send request."
    return redirect('rsr:route-review')


@login_required
def accept_merch_request(request, *args, **kwargs):
    user_id = request.user.id

    user = Account.objects.get(id=user_id)
    payload = {}

    merch_request_id = kwargs.get("request_id")
    if merch_request_id:
        merch_request = Request.objects.get(pk=merch_request_id)
        if merch_request.receiver == user:
            if merch_request:
                merch_request.accept()
                payload['response'] = "Merch request accepted."
            else:
                payload['response'] = "Could not find request."
        else:
            payload['response'] = "This is not your request!"
    else:
        payload['response'] = "Could not find request"
    return redirect('merch:view-merch-request')


@login_required
def StoreData(request, user_id, store_id):
    user = Account.objects.get(username=request.user)
    if (request.user.is_superuser):
        rtmd = Store.objects.all()
    else:
        rtmd = Store.objects.filter(RSRrt=user.username)
        # storedisplay = Store.displays.objects.filter(RSRrt=user.username)

    routeData = get_object_or_404(rtmd, pk=store_id)
    md = Merch.objects.filter(store=routeData).order_by('-completeDate')[:5]
    # displays = Merch.objects.filter(store=routeData)
    return render(request, 'rsr/route-review-data.html', {'store': routeData,
                                                          'merch': md,
                                                          # 'display': displays
                                                          })


@login_required
def decline_merch_request(request, *args, **kwargs):
    user_id = request.user.id

    user = Account.objects.get(id=user_id)
    payload = {}

    merch_request_id = kwargs.get("request_id")
    if merch_request_id:
        merch_request = Request.objects.get(pk=merch_request_id)
        if merch_request.receiver == user:
            if merch_request:
                merch_request.decline()
                payload['response'] = "Merch request accepted."
            else:
                payload['response'] = "Could not find request."
        else:
            payload['response'] = "This is not your request!"
    else:
        payload['response'] = "Could not find request"
    return redirect('merch:view-merch-request')


@login_required(login_url='login')
def item(request):
    template = loader.get_template('merch/product_view.html')
    items = Item.objects.all()

    context = {
        'items': items,
    }
    return HttpResponse(template.render(context, request))


# class orderForm(ListView):
#     model = Item
#     template_name = "order_form2.html"
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['filter'] = ItemFilter(self.request.GET, queryset=self.get_queryset())
#         return context

@login_required(login_url='login')
def merchandise_account(request, store_id, docket_id):
    user_id = request.user.id
    user = Account.objects.get(id=user_id)
    store = Store.objects.get(id=store_id)
    docket = Docket.objects.get(id=docket_id)
    items = Item.objects.all()
    newMerch = Merch(user=user, store=store)
    newMerch.save()
    return render(request=request, template_name="merch/merchandise_account_view.html", context={'store': store,
                                                                                                 'items': items,
                                                                                                 'docket': docket,
                                                                                                 'current_merch': newMerch,
                                                                                                 'upload_form': MerchForm
                                                                                                 })


@login_required
def add_item_order(request, *args, **kwargs):
    user_id = request.user.id

    user = Account.objects.get(id=user_id)
    payload = {}

    item_id = request.POST.get("item_id")
    quantity_str = request.POST.get("quantity")
    store_id = request.POST.get("store_id")
    merch_id = request.POST.get("merch_id")

    try:
        quantity = int(quantity_str)
    except ValueError:
        quantity = quantity_str

    item = Item.objects.get(pk=item_id)
    store = Store.objects.get(pk=store_id)
    merch = Merch.objects.get(pk=merch_id)

    if merch:
        if merch.completeBool is not True:
            if merch.worked_cases.filter(pk=item.id).exists():
                order_item = merch.worked_cases.get(pk=item.id)
                order_item.quantity += quantity
                order_item.save()
                payload['response'] = "Item added to your cart"
            else:
                order_item = merch.worked_cases.create(user=user, item=item, quantity=quantity)
                order_item.save()
                payload['response'] = "Item added to your cart"
        else:
            # ordered_date = timezone.now()
            # order = Merch.objects.create(user=request.user, store=store, ordered_date=ordered_date)
            # order.item.add(item)
            # order_item.quantity += quantity - 1
            # order_item.save()
            payload['response'] = "Item added to your cart"
    else:
        payload['response'] = "Could not find request"
    return redirect("ops:order-form")


def begin_day(request, user):
    user = Account.objects.get(username=user)
    route = Route.objects.get(user=user).pk

    newDock = Docket(user=user, completeBool=True)
    newDock.save()

    return redirect("merch:dashboard")


def complete_day(request, user, docket_id):
    user = Account.objects.get(username=user)
    docket = Docket.objects.get(id=docket_id)
    docket.completeDate = now()
    docket.completeBool = True
    docket.save()

    return redirect("merch:dashboard")


def add_to_oos(request, *args, **kwargs):
    user_id = request.user.id

    user = Account.objects.get(id=user_id)
    payload = {}

    item_id = request.POST.get("item_id")
    bool_val = request.POST.get("bool_val")
    store_id = request.POST.get("store_id")
    merch_id = request.POST.get("merch_id")

    try:
        oos = bool(bool_val)
    except ValueError:
        oos = bool_val

    item = Item.objects.get(pk=item_id)
    store = Store.objects.get(pk=store_id)
    merch = Merch.objects.get(pk=merch_id)

    if oos:
        if merch:
            # if merch.OOS.get(id=item_id).exists():
            #     payload['response'] = "Item added to your cart"
            # else:
            merch.OOS.add(item)
            merch.save()
            payload['response'] = "Item added to your cart"
        else:
            payload['response'] = "Item added to your cart"
    else:
        payload['response'] = "Could not find request"
    return redirect("ops:order-form")


def upload_image(request, *args, **kwargs):
    user_id = request.user.id

    user = Account.objects.get(id=user_id)
    payload = {}

    # item_id = request.POST.get("item_id")
    # bool_val = request.POST.get("bool_val")
    # store_str = request.POST.get("store_id")
    merch_id = request.POST.get("merch_id")
    img = request.POST.get("imgFile")

    # item = Item.objects.get(pk=item_id)

    # try:
    #     store_id = int(store_str)
    # except ValueError:
    #     store_id = store_str

    # store = Store.objects.get(pk=store_str)

    # try:
    #     merch = Merch.objects.get(pk=merch_id)
    # except Merch.DoesNotExist:
    #     merch = Merch(user=user, store=store)
    #     merch.save()

    merch = Merch.objects.get(pk=merch_id)

    if img:
        if merch:
            merch.upload(img)
            merch.save()
            payload['response'] = "Item added to your cart"
        else:
            payload['response'] = "Item added to your cart"
    else:
        payload['response'] = "Could not find request"
    return redirect("ops:order-form")


def complete_merch(request, merch_id, docket_id):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = MerchForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            upload = form.cleaned_data.get('upload')
            merch = Merch.objects.get(pk=merch_id)
            merch.upload = upload
            merch.completeBool = True
            merch.completeDate = now()


            store_id = merch.store.pk
            docket = Docket.objects.get(pk=docket_id)
            docket_store = docket.store_list.get(store=store_id)
            docket_store.complete = True

            docket.merch_list.add(merch)
            merch.AmountCalculator()

            docket_store.save()
            merch.save()

            return redirect("merch:dashboard")

    # if a GET (or any other method) we'll create a blank form
    else:
        form = MerchForm()

    return redirect("merch:dashboard")


def plan_day(request, user_id, year, month, day):
    user = Account.objects.get(pk=user_id)

    date = datetime(year=year, month=month, day=day)


    if user.is_rsr():
        route = Store.objects.filter(RSRrt=user.route_number)
    elif user.is_merch():
        route = Store.objects.filter(merchandiser__store=user.id)
    elif user.is_superuser:
        route = Store.objects.all()

    if Docket.objects.filter(planDate=date, user=user).exists():
        docket = Docket.objects.get(planDate=date, user=user)
        stores = docket.store_list.all()
        template = loader.get_template('merch/merchandiser_dashboard_view.html')
        data = {
            'docket': docket,
            'stores': route,
            'route': route,
            'requests': merch_request
        }
    else:
        docket = Docket(user=user, completeBool=False, planDate=date)
        docket.save()
        stores = docket.store_list.all()
        data = {
            'docket': docket,
            'stores': route,
            'route': route,
            'requests': merch_request
        }
    return render(request, 'merch/plan_day.html', data)


def add_to_plan(request, *args, **kwargs):
    user_id = request.user.id

    user = Account.objects.get(id=user_id)
    payload = {}

    store_id = request.POST.get("store_id")
    docket_id = request.POST.get("docket_id")

    store = Store.objects.get(pk=store_id)
    docket = Docket.objects.get(pk=docket_id)

    if docket:
        if store:
            # if merch.OOS.get(id=item_id).exists():
            #     payload['response'] = "Item added to your cart"
            # else:
            count = docket.store_list.count()
            storeItem = StoreListItem(user=user,store=store,position=count+1)

            storeItem.save()
            docket.store_list.add(storeItem)
            docket.save()
            payload['response'] = "Item added to your cart"
        else:
            payload['response'] = "Item added to your cart"
    else:
        payload['response'] = "Could not find request"
    return redirect("ops:order-form")


def plan_request(request, *args, **kwargs):
    payload = {}

    user_id = request.POST.get("user_id")
    date = request.POST.get("plan_date")

    user = Account.objects.get(id=user_id)

    if user.is_rsr():
        route = Store.objects.filter(RSRrt=user.route_number)
    elif user.is_merch():
        route = Store.objects.filter(merchandiser__store=user.id)
    elif user.is_superuser:
        route = Store.objects.all()

    if Docket.objects.get(planDate=date, user=user):
        docket = Docket.objects.get(planDate=date, user=user)
        stores = docket.store_list.all()
        template = loader.get_template('merch/merchandiser_dashboard_view.html')
        context = {
            'docket': docket,
            'stores': stores,
            'route': route,
            'requests': merch_request
        }
        return HttpResponse(template.render(context, request))
    else:
        docket = Docket(user=user, completeBool=False, planDate=date)
        docket.save()
        stores = docket.store_list.all()
        data = {
            'docket': docket,
            'stores': stores,
            'route': route,
            'requests': merch_request
        }
        payload['response'] = data
    return redirect("merch:dashboard")
