from django.test import TestCase
from accounts.models import (
    ProviderWallet,
    RequestCharge,
    PhoneNumber,
    ProviderAccount,
    ProviderAccountTeamMember,
)
from django.contrib.auth import get_user_model

User = get_user_model()


class RequestChargeEdgeCaseTest(TestCase):
    def setUp(self):
        self.provider_account = ProviderAccount.objects.create(
            name="Test Provider Account"
        )
        self.phone_number = PhoneNumber.objects.create(number="1234567890")
        self.user = User.objects.create(username="test_user")
        self.requester = ProviderAccountTeamMember.objects.create(
            user_id=self.user.id,
            account=self.provider_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.ADMIN,
        )
        self.initial_balance = 10000
        self.provider_wallet = ProviderWallet.objects.create(
            account=self.provider_account, balance=self.initial_balance
        )

    def test_insufficient_balance_single_request(self):
        charge_amount = self.initial_balance + 1000

        with self.assertRaisesRegex(
            ValueError, "Insufficient balance in provider account."
        ):
            RequestCharge.create_charge_safely(
                phone_number_id=self.phone_number.id,
                provider_account_id=self.provider_account.id,
                user_id=self.requester.user_id,
                amount=charge_amount,
            )

        self.assertEqual(RequestCharge.objects.count(), 0)
        self.provider_wallet.refresh_from_db()  # Get updated balance from DB
        self.assertEqual(self.provider_wallet.balance, self.initial_balance)

    def test_exact_balance_request(self):
        charge_amount = self.initial_balance

        charge = RequestCharge.create_charge_safely(
            phone_number_id=self.phone_number.id,
            provider_account_id=self.provider_account.id,
            user_id=self.requester.user_id,
            amount=charge_amount,
        )

        self.assertIsNotNone(charge)
        self.assertEqual(RequestCharge.objects.count(), 1)
        self.assertEqual(charge.amount, charge_amount)
        self.provider_wallet.refresh_from_db()
        self.assertEqual(self.provider_wallet.balance, 0)

    def test_zero_amount_request(self):
        charge_amount = 0

        with self.assertRaisesRegex(ValueError, "Charge amount must be positive."):
            RequestCharge.create_charge_safely(
                phone_number_id=self.phone_number.id,
                provider_account_id=self.provider_account.id,
                user_id=self.requester.user_id,
                amount=charge_amount,
            )
        self.assertEqual(RequestCharge.objects.count(), 0)
        self.provider_wallet.refresh_from_db()
        self.assertEqual(self.provider_wallet.balance, self.initial_balance)

    def test_non_existent_provider_account(self):
        non_existent_id = self.provider_account.id + 999
        charge_amount = 1000

        with self.assertRaisesRegex(ValueError, "Provider wallet not found."):
            RequestCharge.create_charge_safely(
                phone_number_id=self.phone_number.id,
                provider_account_id=non_existent_id,
                user_id=self.requester.user_id,
                amount=charge_amount,
            )
        self.assertEqual(RequestCharge.objects.count(), 0)
        self.provider_wallet.refresh_from_db()
        self.assertEqual(self.provider_wallet.balance, self.initial_balance)

    def test_low_permission_provider_account_team_member(self):
        low_permission_user = User.objects.create(username="low_permission_user")
        low_permission_team_member = ProviderAccountTeamMember.objects.create(
            account=self.provider_account,
            user=low_permission_user,
            permission_level=ProviderAccountTeamMember.PermissionLevel.USER,
        )
        charge_amount = 1000

        with self.assertRaisesRegex(
            PermissionError,
            "The Requester user does not have permission to this action",
        ):
            RequestCharge.create_charge_safely(
                phone_number_id=self.phone_number.id,
                provider_account_id=self.provider_account.id,
                user_id=low_permission_team_member.user_id,
                amount=charge_amount,
            )
        self.assertEqual(RequestCharge.objects.count(), 0)
        self.provider_wallet.refresh_from_db()
        self.assertEqual(self.provider_wallet.balance, self.initial_balance)

    def test_non_existent_phone_number(self):
        non_existent_id = self.phone_number.id + 999
        charge_amount = 1000

        with self.assertRaisesRegex(ValueError, "Phone number not found."):
            RequestCharge.create_charge_safely(
                phone_number_id=non_existent_id,
                provider_account_id=self.provider_account.id,
                user_id=self.requester.user_id,
                amount=charge_amount,
            )
        self.assertEqual(RequestCharge.objects.count(), 0)
        self.provider_wallet.refresh_from_db()
        self.assertEqual(self.provider_wallet.balance, self.initial_balance)

    def test_non_existent_requester(self):
        non_existent_user_id = self.requester.user_id + 999
        charge_amount = 1000

        with self.assertRaisesRegex(ValueError, "Requester not found."):
            RequestCharge.create_charge_safely(
                phone_number_id=self.phone_number.id,
                provider_account_id=self.provider_account.id,
                user_id=non_existent_user_id,
                amount=charge_amount,
            )

        self.assertEqual(RequestCharge.objects.count(), 0)
        self.provider_wallet.refresh_from_db()
        self.assertEqual(self.provider_wallet.balance, self.initial_balance)

    def test_multiple_requests_partial_success(self):

        self.provider_wallet.balance = 1000
        self.provider_wallet.save()
        initial_balance_for_test = 1000

        charges_to_attempt = [500, 300, 500]
        successful_charges_count = 0
        final_balance = initial_balance_for_test

        for amount in charges_to_attempt:
            try:
                RequestCharge.create_charge_safely(
                    phone_number_id=self.phone_number.id,
                    provider_account_id=self.provider_account.id,
                    user_id=self.requester.user_id,
                    amount=amount,
                )
                successful_charges_count += 1
                final_balance -= amount
            except ValueError as e:
                self.assertIn("Insufficient balance", str(e))
            except Exception as e:
                self.fail(f"Unexpected exception: {e}")

        self.assertEqual(RequestCharge.objects.count(), successful_charges_count)
        self.provider_wallet.refresh_from_db()
        self.assertEqual(self.provider_wallet.balance, final_balance)
        self.assertEqual(successful_charges_count, 2)

