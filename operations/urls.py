from django.contrib.auth.decorators import login_required
from django.urls import path
from operations import views
from operations.views import orderForm, ProductView, add_to_cart, add_item_order, place_order_view, list_items_view, \
    update_order
from .views import review_order_view
from django.urls import path

app_name = "ops"

urlpatterns = [
    # Cart
    path('add-to-cart', add_item_order, name='add-to-cart'),
    path('add-to-cart/<int:pk>/<int:quantity>/', add_to_cart, name='add-to-cart-item-quantity'),
    # path('remove-from-cart/<pk>/', remove_from_cart, name='remove-from-cart'),
    # path('reduce-quantity-item/<pk>/', reduce_quantity_item, name='reduce-quantity-item'),
    path('product/<pk>/', ProductView.as_view(), name='product'),
    path('orderform', login_required(orderForm.as_view()), name='order-form'),

    # Order
    path('warehouse/<int:warehouse_id>/orderform', login_required(orderForm.as_view()), name='warehouse-orderform'),
    path('warehouse/<int:warehouse_id>/order/', list_items_view, name='warehouse-order'),
    path('warehouse/<int:warehouse_id>/inventory/', views.inventory_view, name='warehouse-inventory'),
    # path('warehouse/<int:warehouse_id>/inventory/physical', views.WarehouseDateForm, name='warehouse-physical-inventory'),

    path('place_order/', place_order_view, name='place_order'),
    path('review_order/', views.review_order_view, name='review_order'),
    path('submit_order/', views.submit_order, name='submit_order'),

    path('order-summary', views.OrderSummaryView, name='order-summary'),
    path('order-summary/<int:order_id>', views.OrderSummaryViewWithID, name='order-summary'),
    path('data/<int:item_id>', views.ItemData, name='item-data'),

    path('dashboard/', views.WarehouseList, name='warehouse-dash'),
    path('warehouse/dashboard/', views.WarehouseList, name='warehouse-dash'),

    path('warehouse/<int:warehouse_id>', views.warehouse_dashboard, name='warehouse-detail'),
    path('warehouse/<int:warehouse_id>/warehousemanager', views.WarehouseManagerDetail, name='warehouse-detail'),

    # path('warehouse-dates', views.WarehouseDateItemView, name='warehouse-dates'),
    # path('warehouse-dates/input', views.WarehouseDateForm, name='warehouse-dates-form'),
    # path('warehouse-dates/<int:item_id>/<int:inventory_id>/skip', views.WarehouseDateFormSkip, name='warehouse-dates-form-skip'),
    # path('warehouse-dates/<int:item_id>', views.WarehouseDateItemForm, name='warehouse-date-form'),
    # path('warehouse-dates/<int:item_id>/<int:inventory_id>/input', views.WarehouseDateItemInput, name='warehouse-date-input'),

    # Print pallet pages
    path('warehouse/<int:route_id>/print/pallet/', views.PalletPages, name='print-pallet-pages'),
    path('warehouse/<int:warehouse_id>/print/', views.PrintPalletPages, name='print-pallet-pages'),

    # Orders
    path('warehouse/order/', views.orders_view, name='order_view'),
    path('warehouse/order/<str:order_id>/', views.order_detail_view, name='detail_order_view'),

    # Order_Status
    path('warehouse/order-status-update/<int:order_id>/update', views.WarehouseManagerOrderStatusUpdate, name='whmosu'),
    path('warehouse/order-status-view/', views.WarehouseManagerOrderStatusView, name='whmosv'),
    path('warehouse/order-status-view/<int:order_id>/', views.WarehouseManagerOrderStatusDetail, name='whmosv'),

    path('warehouse/order/<str:order_id>/pdf/', views.generate_order_pdf, name='generate_order_pdf'),
    path('warehouse/order/<str:order_id>/complete/', views.complete_order, name='complete_order'),
    path('warehouse/order/<str:order_id>/prepare/', views.prepare_order, name='prepare_order'),
    path('warehouse/order/<str:order_id>/verify/', views.verify_order, name='verify_order'),
    path('warehouse/order/<str:order_id>/edit/', views.verify_order, name='edit_order'),

    # Inventory
    path('warehouse/<int:warehouse_id>/inventory/', views.inventory_view, name='inventory'),
    path('warehouse/<int:warehouse_id>/runrates/', views.inventory_with_6week_avg, name='run_rates'),
    path('warehouse/<int:warehouse_id>/trends/<str:item_type>/', views.weekly_trend_view, name='trends'),
    path('warehouse/<int:warehouse_id>/comparison/', views.comparison_across_weeks_view, name='comparison'),

    # Edit Orders
    path('warehouse/order/<str:order_id>/update/', views.update_order, name='update_order'),
    path('warehouse/order/<str:order_id>/add/items/', views.add_items, name='add_items'),

    # API
    path('api/trigger-process-order/', views.trigger_process_order, name='trigger_process_order'),
    path('api/update-builder/<str:order_id>/', views.update_builder, name='update_builder'),


    # Test
    path('test', views.test_redis, name='test_cache'),

]
