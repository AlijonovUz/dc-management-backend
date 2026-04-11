from drf_spectacular.utils import extend_schema
from rest_framework import parsers
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny

from apps.applications.models import Application
from apps.applications.serializers import ApplicationCreateSerializer, ApplicationStatusUpdateSerializer
from apps.users.permissions import IsAdmin, IsManager, IsSuperAdmin


@extend_schema(tags=['Applications'])
class ApplicationCreateView(CreateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationCreateSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    permission_classes = (AllowAny,)


@extend_schema(tags=['Applications'])
class ApplicationStatusUpdateView(UpdateAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationStatusUpdateSerializer
    permission_classes = (IsSuperAdmin | IsAdmin | IsManager,)
    http_method_names = ('patch',)
