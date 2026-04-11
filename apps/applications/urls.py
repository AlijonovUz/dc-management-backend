from django.urls import path

from .views import ApplicationCreateView, ApplicationStatusUpdateView


urlpatterns = [
    path('applications/', ApplicationCreateView.as_view(), name='application-create'),
    path('applications/<int:pk>/status/', ApplicationStatusUpdateView.as_view(), name='application-status-update'),
]