from django.urls import path
from operations import views
from operations.views import place_order_view, list_items_view

app_name = "ops"

urlpatterns = [


    # Order
    # path('warehouse/<int:warehouse_id>/order/', list_items_view, name='warehouse-order'),
    # path('warehouse/<int:warehouse_id>/inventory/', views.inventory_view, name='warehouse-inventory'),

    path('place_order/', place_order_view, name='place_order'),
    path('review_order/', views.review_order_view, name='review_order'),
    path('submit_order/', views.submit_order, name='submit_order'),

    path('warehouse/dashboard/', views.warehouse_dashboard, name='warehouse-detail'),

    # Write Order
    path('warehouse/order/create/', views.create_order, name='create'),

    # Orders
    path('warehouse/order/', views.orders_view, name='order_view'),
    path('warehouse/order/<str:order_id>/', views.order_detail_view, name='detail_order_view'),


    path('warehouse/order/<str:order_id>/pdf/', views.generate_order_pdf, name='generate_order_pdf'),
    path('warehouse/order/<str:order_id>/complete/', views.complete_order, name='complete_order'),
    path('warehouse/order/<str:order_id>/prepare/', views.prepare_order, name='prepare_order'),
    path('warehouse/order/<str:order_id>/verify/', views.verify_order, name='verify_order'),
    path('warehouse/order/<str:order_id>/edit/', views.verify_order, name='edit_order'),

    # Inventory
    path('warehouse/inventory/', views.inventory_view, name='inventory'),
    path('warehouse/runrates/', views.inventory_with_6week_avg, name='run_rates'),
    path('warehouse/trends/<str:item_type>/', views.weekly_trend_view, name='trends'),
    path('warehouse/comparison/', views.comparison_across_weeks_view, name='comparison'),

    # Edit Orders
    path('warehouse/order/<str:order_id>/update/', views.update_order, name='update_order'),
    path('warehouse/order/<str:order_id>/add/items/', views.add_items, name='add_items'),

    # API
    path('api/trigger-process-order/', views.trigger_process_order, name='trigger_process_order'),
    path('api/update-builder/<str:order_id>/', views.update_builder, name='update_builder'),
    path('api/delete-item/<str:item_id>/', views.update_builder, name='update_builder'),
]
