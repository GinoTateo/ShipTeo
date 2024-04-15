from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from account.models import Account
from merch.models import Merch
from rsr.models import Store, Route


@login_required
def RouteReview(request, *args, **kwargs):
    context = {}
    user_id = request.user.id
    user = Account.objects.get(pk=user_id)
    if user.is_authenticated:
        if user:
            store_list = Route.objects.get(user=user)
            context['list'] = store_list.store.all()
        else:
            return HttpResponse("You cant view another users route!")
    else:
        redirect('Login')
    return render(request, "rsr/route-review.html", context)

@login_required
def StoreData(request, user_id, store_id):
        user = Account.objects.get(username=request.user)
        if (request.user.is_superuser):
            rtmd = Store.objects.all()
        else:
            rtmd = Store.objects.filter(RSRrt=user.username)
            #storedisplay = Store.displays.objects.filter(RSRrt=user.username)

        routeData = get_object_or_404(rtmd, pk=store_id)
        md = Merch.objects.filter(store=routeData).order_by('-startDate')[:5]
        #displays = Merch.objects.filter(store=routeData)
        return render(request, 'rsr/route-review-data.html', {'store': routeData,
                                                          'merch': md,
                                                              #'display': displays
                                                              })
