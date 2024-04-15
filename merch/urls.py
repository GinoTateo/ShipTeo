from django.contrib.auth.decorators import login_required
from django.urls import path
from django.conf.urls.static import static
from MerchManagerV1 import settings
from . import views

app_name = "merch"

urlpatterns = [

    # Base
    path('', views.index, name='index'),

    #Dashboard views
    path('dashboard', views.dashboard, name='dashboard'),
    path('<int:merch_id>/', views.detail, name='detail'),
    path('data/<int:user_id>/<int:store_id>', views.StoreData, name='store-data'),
    path('docket/<int:user_id>/', views.docket, name='docket'),
    path('items', views.item, name='item'),
    path('route', views.route, name='item'),

    # Requests
    path('merch_request/', views.merch_request, name='view-merch-request'),
    path('accept_merch_request/<int:request_id>', views.accept_merch_request, name='accept-merch-request'),
    path('decline_merch_request/<int:request_id>', views.decline_merch_request, name='decline-merch-request'),
    path('merch_request/<receiver_id>/<store_id>', views.send_merch_request, name='send-merch-request'),
    path('cancel_merch_request/<receiver_id>/<store_id>/', views.cancel_merch_request, name='cancel-merch-request'),
    path('plan-request/', views.plan_request, name='plan-request'),

    # Merchandising
    path('merchandise_account/<int:store_id>/<int:docket_id>', views.merchandise_account , name='account-merch'),
    path('begin-day/<user>', views.begin_day, name='begin-day'),
    path('plan-day/<int:user_id>/<int:year>-<int:month>-<int:day>', views.plan_day, name='begin-day'),
    path('add-to-plan/', views.add_to_plan, name='add-to-plan'),
    path('complete-day/<user>/<int:docket_id>', views.complete_day, name='complete-day'),
    path('add-to-order/', views.add_item_order, name='add-to-order'),
    path('add-to-oos/', views.add_to_oos, name='add-to-oos'),
    path('complete-merch/<int:merch_id>/<int:docket_id>', views.complete_merch, name='complete-merch'),
    path('upload-image/', views.upload_image, name='upload-img'),

    # # Add
    # path('add', views.add, name='add toolbar'),
    # path('add/store', views.addStore, name='create merch'),
    # path('add/merch', views.addMerch, name='create merch'),
    # path('add/EOW', views.addWD, name='create merch'),
    # path('add/Item', views.addItem, name='create merch'),

    # Merch
    # path('<int:merch_id>/', views.detail, name='detail'),
    # # path('<merchuser>/', views.merchuser, name='merch-user'),
    # path('weekly', views.weekly, name='weekly-data'),
    # path('dashboard', views.dashboard, name='dashboard'),
    # path('merchrequest', views.merch_request, name='requests'),
    # path('merchrequest/', views.merch_request, name='requests'),
    # path('accept_merch_request/<merch_request_id>', views.accept_merch_request, name='accept_request'),
    #
    # path('create-merch/<storeid>', views.create_merch, name='create-merch'),
    # #path('data', views.merchuser, name='merch-user'), /<storeid>
    #
    # # Route
    # path('route-review', views.RouteReview, name='route-review'),
    # path('order-summary', views.OrderSummaryView, name='order-summary'),
    # path('/data/<int:user_id>/<int:store_id>', views.StoreData, name='order-summary-data'),
    #
    # # Reports
    # path('send', views.send_email, name='send-email'),

]
