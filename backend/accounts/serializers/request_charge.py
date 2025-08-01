from rest_framework import serializers

from rest_framework.exceptions import PermissionDenied

from accounts.models import RequestCharge, PhoneNumber, ProviderAccount
from core.utils import PhoneNumberRegexValidation


class RequestChargeCreateSerializer(serializers.ModelSerializer):
    provider_account = serializers.PrimaryKeyRelatedField(
        queryset=ProviderAccount.objects.filter(is_active=True),
    )
    phone_number = serializers.CharField(validators=[PhoneNumberRegexValidation])
    amount = serializers.IntegerField(min_value=0)

    class Meta:
        model = RequestCharge
        fields = ["phone_number", "provider_account", "amount"]

    def create(self, validated_data):
        phone_number = validated_data.pop("phone_number")

        provider_account_instance = validated_data.pop("provider_account")
        amount = validated_data.pop("amount")
        user = (
            self.context.get("request").user
            if self.context.get("request")
            and self.context["request"].user.is_authenticated
            else None
        )

        try:
            phone_number_instance = PhoneNumber.objects.get(number=phone_number)
            request_charge = RequestCharge.create_charge_safely(
                phone_number_id=phone_number_instance.id,
                provider_account_id=provider_account_instance.id,
                amount=amount,
                user_id=user.id,
            )
            return request_charge
        except PermissionError as e:
            raise PermissionDenied()
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)})
        except PhoneNumber.DoesNotExist:
            raise serializers.ValidationError(
                {"derail": "The Phone Number Does not exist"}
            )
        except Exception as e:  # TODO should be remove to monitor error 500
            raise serializers.ValidationError(
                {"detail": "An unexpected error occurred during charge creation."}
            )


class RequestChargeDetailSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="provider_account.name", read_only=True)
    number = serializers.CharField(source="phone_number.number",read_only=True)
    
    
    class Meta:
        model = RequestCharge
        fields = ["number", "account_name", "amount"]