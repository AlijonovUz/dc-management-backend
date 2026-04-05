from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, generics, filters
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (UserSerializer, ProfileSerializer, ChangePasswordSerializer,
                          MyTokenRefreshSerializer, MyTokenObtainPairSerializer)
from .permissions import IsSuperAdmin

User = get_user_model()


@extend_schema(tags=['Users'], summary="SuperAdmin")
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'first_name', 'last_name']


@extend_schema(tags=['Profile'])
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Profile"])
class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['put']

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Authorization"])
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


@extend_schema(tags=["Authorization"])
class MyTokenRefreshView(TokenRefreshView):
    serializer_class = MyTokenRefreshSerializer
