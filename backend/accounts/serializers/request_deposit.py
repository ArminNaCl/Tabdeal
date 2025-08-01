from rest_framework import serializers

from accounts.models import RequestDeposit
from rest_framework.exceptions import PermissionDenied


from accounts.models import RequestDeposit, PhoneNumber, ProviderAccount


class RequestDepositCreateSerializer(serializers.ModelSerializer):

    account = serializers.PrimaryKeyRelatedField(
        queryset=ProviderAccount.objects.filter(is_active=True),
    )
    amount = serializers.IntegerField(min_value=0)

    class Meta:
        model = RequestDeposit
        fields = (
            "amount",
            "account",
        )

    def create(self, validated_data):
        try:
            instance = super().create(validated_data)
            return instance
        except PermissionError:
            raise PermissionDenied()
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)})
        except PhoneNumber.DoesNotExist:
            raise serializers.ValidationError(
                {"derail": "The Phone Number Does not exist"}
            )

    def validate(self, data):
        if self.instance:
            return data
        user = (
            self.context.get("request").user
            if self.context.get("request")
            and self.context["request"].user.is_authenticated
            else None
        )
        data["requester"] = user.team
        temp_instance = RequestDeposit(
            requester=data.get("requester"),
            amount=data.get("amount"),
            account=data.get("account"),
        )
        temp_instance.full_clean()
        return data


class RequestDepositSerializer(serializers.ModelSerializer):
    requester_username = serializers.CharField(
        source="requester.user.username", read_only=True
    )
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = RequestDeposit
        fields = (
            "id",
            "requester_username",
            "account_name",
            "amount",
            "status",
            "created",
            "updated",
        )
        read_only_fields = fields


class RequestDepositDetailSerializer(RequestDepositSerializer):
    comment = serializers.TimeField(read_only=True)
    assignee_username = serializers.CharField(
        source="assignee.username", read_only=True
    )

    class Meta:
        model = RequestDeposit
        fields = RequestDepositSerializer.Meta.fields + ("comment", "assignee_username")
