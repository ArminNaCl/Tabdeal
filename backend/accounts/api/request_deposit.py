from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


from drf_spectacular.utils import extend_schema, OpenApiExample, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers  # Import serializers for inline_serializer

from accounts.models import RequestDeposit
from accounts.serializers import (
    RequestDepositCreateSerializer,
    RequestDepositDetailSerializer,
    RequestDepositSerializer,
)


@extend_schema(
    summary="Create a Deposit Request for an account",
    request=RequestDepositCreateSerializer,
    responses={
        201: RequestDepositDetailSerializer,
        400: inline_serializer(
            name="ErrorResponse",
            fields={
                "detail": serializers.CharField(),
                "user_id": serializers.ListField(
                    child=serializers.CharField(), required=False
                ),
                "non_field_errors": serializers.ListField(
                    child=serializers.CharField(), required=False
                ),
            },
        ),
    },
)
@extend_schema(
    summary= "List of all created request deposits",
    methods=["GET"],
    responses={
        200: RequestDepositSerializer(many=True),
        401: {},
    },
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def request_deposit_list_create(request):
    """
    API View for listing all deposit requests or creating a new one.
    """
    if request.method == "GET":
        #TODO if request.user == Admin filter by Account if Staff created and not hich
        deposit_requests = RequestDeposit.objects.all().order_by("-created")
        serializer = RequestDepositDetailSerializer(deposit_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        serializer = RequestDepositCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(RequestDepositDetailSerializer(instance).data,status=status.HTTP_201_CREATED)


@extend_schema(
    summary = "Get Detail of existing Deposit Request",
    methods=["GET"],
    responses={
        200: RequestDepositDetailSerializer,
        404: {},  # Or more specific error like detail: "Not found."
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def request_deposit_detail(request, pk):
    """
    API View for retrieving or deleting a single RequestDeposit instance.
    """
    try:
        instance = RequestDeposit.objects.get(id=pk)
    except RequestDeposit.DoNotExist:
        return Response(
            {"error": "object does not exist"}, status=status.HTTP_404_NOT_FOUND
        )

    serializer = RequestDepositDetailSerializer(instance)
    return Response(serializer.data, status=status.HTTP_200_OK)
