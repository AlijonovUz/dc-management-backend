from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import (UserViewSet, ProfileView, ChangePasswordView,
                    MyTokenObtainPairView, MyTokenRefreshView)

router = SimpleRouter()
router.register('users', UserViewSet)

urlpatterns = [
    path('users/me/', ProfileView.as_view()),
    path('users/me/change-password/', ChangePasswordView.as_view()),

    path('', include(router.urls)),

    path("auth/login/", MyTokenObtainPairView.as_view()),
    path("auth/refresh/", MyTokenRefreshView.as_view()),
]
