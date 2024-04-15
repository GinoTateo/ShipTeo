from django.urls import path

from rsr import views

app_name = "rsr"
urlpatterns = [
    # Route
    path('route-review', views.RouteReview, name='route-review'),
    path('/data/<int:user_id>/<int:store_id>', views.StoreData, name='store-data'),

    ]