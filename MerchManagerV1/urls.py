"""MerchManagerV1 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.urls import path, include
from account import views

urlpatterns = [

    # app patterns
    path('admin/', admin.site.urls),
    path('account/', include('account.urls')),
    # path('merch/', include('merch.urls')), Branched into its own plateform
    path('ops/', include('operations.urls')),
    # path('rsr/', include('rsr.urls')),
    # path('api/', include('api.urls')),

    # Service & Pricing
    # path('service', views.service, name='service'),

    # Home
    path('', views.home, name='home'),
    path('home', views.home, name='home'),

    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('register', views.register_view, name='register'),
    # path('register', views.login_view, name='register'),

    # path('home', views.home, name='index'),
    # path('account/', views.account, name='account'),

    #
    path('accounts/login/', views.login_view, name='login'),
    #
    # #
    # path('add/', views.add, name='index'),
    # path('add/store', views.addStore, name='create store'),
    # path('add/merch', views.addMerch, name='create merch'),
    # path('add/EOW', views.addWD, name='create EOW'),
    # path('add/Item', views.addItem, name='create item'),
    #
    # #
    # path('merchrequest', views.merch_request, name='requests'),
    #
    # #
    # path('route-review', views.RouteReview, name='route-review'),
    # path('merch/data/<int:user_id>/<int:store_id>', views.StoreData, name='route-review-data'),
    # path('merch/store/<int:user_id>/<int:store_id>', views.SpecificStoreMerch, name='specific-store-data'),

    # url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    # url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
