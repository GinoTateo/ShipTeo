import json

from django.contrib.auth import login
from django.http import request, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from pymongo import MongoClient
from rest_framework import permissions, status, generics, viewsets
from rest_framework import views
from rest_framework.decorators import api_view
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from account.models import Account
from api.serializer import UserSerializer, MerchSerializer, StoreSerializer, RequestSerializer, \
    DocketSerializer, RouteSerializer, LoginSerializer
from merch.models import Merch, Request, Docket
from rsr.models import Store, Route



class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = UserSerializer
    #permission_classes = [permissions.IsAuthenticated]


class LoginView(views.APIView):
    # This view should be accessible also for unauthenticated users.
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=self.request.data,
                                     context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(None, status=status.HTTP_202_ACCEPTED)


class ProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class MerchView(generics.RetrieveAPIView):
    queryset = Merch.objects.all()
    serializer_class = MerchSerializer


@api_view(['POST'])
def CreateMerchView(request):
    serializer = MerchSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StoreView(generics.RetrieveAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer


class RouteView(generics.RetrieveAPIView):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer


class UserRouteView(RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        userRoute = Route.objects.get(user=request.user)
        ser = RouteSerializer(userRoute)
        return Response(ser.data)


class RequestView(generics.RetrieveAPIView):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer


@api_view(['POST'])
def PostRequestView(request):
    serializer = RequestSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DocketView(generics.RetrieveAPIView):
    queryset = Docket.objects.all()
    serializer_class = DocketSerializer


@api_view(['POST'])
def CreateDocketView(request):
    serializer = DocketSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# @require_POST
# @csrf_exempt  # Use this cautiously and consider CSRF protection
# def update_item(request):
#     try:
#         data = json.loads(request.body.decode('utf-8'))
#         order_id = data['order_id']
#         item_id = data['item_id']
#         quantity = data['quantity']
#         inStock = data['inStock'] == 'true'
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
#
#     try:
#         uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
#         client = MongoClient(uri)
#         db = client['mydatabase']
#         collection = db['orders']
#
#         result = collection.update_one(
#             {'_id': order_id, 'items.ItemNumber': item_id},
#             {'$set': {'items.$.Quantity': quantity}}
#             # For updating InStock as well, add it to the $set dict
#             # , 'items.$.InStock': inStock
#         )
#
#         client.close()
#
#         if result.modified_count:
#             return JsonResponse({"message": "Item updated successfully"})
#         else:
#             return JsonResponse({"error": "Item not found or no update needed."}, status=404)
#
#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=500)
