from django.urls import path, include
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from api import views

router = routers.DefaultRouter()
router.register(r'account', views.AccountViewSet)




urlpatterns = [
    #Account
    path('login/', views.LoginView.as_view()),
    path('profile/', views.ProfileView.as_view()),

    # Auth Token
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),

    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),

    #Merch (Specific Merch via PK, Post Merch, NEED GET ALL FUNCTION)
    path('get_merch/<pk>', views.MerchView.as_view()),
    path('post_merch/', views.CreateMerchView),

    #Store (Specific Stores via PK)
    path('get_store/<pk>', views.StoreView.as_view()),

    #Route (Specific Route via PK)
    path('get_route/<pk>', views.RouteView.as_view()),
    path('get_user_route/', views.UserRouteView.as_view()),

    #Request (Specific Requests via PK, NEED GET ALL FUNCTION)
    path('get_request/<pk>', views.RequestView.as_view()),
    path('post_request/', views.PostRequestView),

    #Docket (Specific Docket via PK, Post Docket, NEED GET ALL FUNCTION)
    path('get_docket/<pk>', views.DocketView.as_view()),
    path('post_docket/', views.CreateDocketView),

]