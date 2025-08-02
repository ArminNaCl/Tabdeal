from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


from drf_spectacular.utils import extend_schema


from accounts.models import RequestDeposit,ProviderAccountTeamMember
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
        400: {"description": "Bad Request"},
        403: {"description": "user dont have permission"},
    },
)
@extend_schema(
    summary="List of all created request deposits",
    methods=["GET"],
    responses={
        200: RequestDepositSerializer(many=True),
        400: {"description": "Bad Request"},
        403: {"description": "user dont have permission"},
    },
)
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def request_deposit_list_create(request):
    """
    API View for listing all deposit requests or creating a new one.
    """
    if request.method == "GET":
        queryset = RequestDeposit.objects.all()
        if request.user.is_admin:
            queryset=queryset
        elif request.user.tame.permission_level == ProviderAccountTeamMember.PermissionLevel.ADMIN:
            queryset = queryset.filter(account=request.user.team.account)
        elif request.user.tame.permission_level == ProviderAccountTeamMember.PermissionLevel.STAFF:
            queryset = queryset.filter(user_id=request.user.id)
        else:
            queryset= queryset.none
        deposit_requests = queryset.order_by("-created")
        serializer = RequestDepositDetailSerializer(deposit_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        serializer = RequestDepositCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(
            RequestDepositDetailSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="Get Detail of existing Deposit Request",
    methods=["GET"],
    responses={
        200: RequestDepositDetailSerializer,
        404: {"description": "Objects Not Found"},
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def request_deposit_detail(request, pk):

    try:
        instance = RequestDeposit.objects.get(id=pk)
    except RequestDeposit.DoesNotExist:
        return Response(
            {"error": "object does not exist"}, status=status.HTTP_404_NOT_FOUND
        )

    serializer = RequestDepositDetailSerializer(instance)
    return Response(serializer.data, status=status.HTTP_200_OK)
