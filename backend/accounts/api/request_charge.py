from django.shortcuts import render

# Create your views here.

from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from drf_spectacular.utils import extend_schema
from accounts.serializers.request_charge import RequestChargeCreateSerializer,RequestChargeDetailSerializer


@extend_schema(
    summary="Create a Charge Request from an account to a number",
    request=RequestChargeCreateSerializer,
    responses={
        201: RequestChargeDetailSerializer,
        400: {"description": "Bad Request"},
        403: {"description": "user dont have permission"},
    },
    methods=["POST"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def request_charge_api_view(request):

    serializer = RequestChargeCreateSerializer(
        data=request.data, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)
    instance = serializer.save()
    return Response(RequestChargeDetailSerializer(instance).data, status=status.HTTP_201_CREATED)
