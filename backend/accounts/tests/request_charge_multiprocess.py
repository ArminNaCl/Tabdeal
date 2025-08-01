import threading
from django.test import TestCase
from django.db import transaction, connection, connections
from django.test import TransactionTestCase
from accounts.models import (
    ProviderWallet,
    RequestCharge,
    PhoneNumber,
    ProviderAccount,
    ProviderAccountTeamMember,
)
from django.contrib.auth import get_user_model

User = get_user_model()



class RequestChargeRaceConditionTest(TransactionTestCase):
    def setUp(self):
        self.provider_account = ProviderAccount.objects.create(
            name="Concurrent Test Provider"
        )
        self.phone_number = PhoneNumber.objects.create(number="9876543210")
        self.user = User.objects.create(username="test_user")
        self.requester = ProviderAccountTeamMember.objects.create(
            user_id=self.user.id,
            account=self.provider_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.ADMIN,
        )
        self.initial_balance = 50000
        self.charge_amount = 10000
        self.provider_wallet = ProviderWallet.objects.create(
            account=self.provider_account, balance=self.initial_balance
        )

    def _charge_task(
        self, phone_number_id, provider_account_id, user_id, amount, results_list
    ):
        db_connection = connections["default"]
        try:
            db_connection.close()
            charge = RequestCharge.create_charge_safely(
                phone_number_id=phone_number_id,
                provider_account_id=provider_account_id,
                user_id=user_id,
                amount=amount,
            )
            results_list.append(True)
        except ValueError as e:
            results_list.append(False)
        except Exception as e:
            results_list.append(f"Error: {type(e).__name__} - {e}")
        finally:
            db_connection.close()

    def test_concurrent_charges_with_race_condition_simulation(self):
        num_concurrent_requests = 10

        expected_successful_charges = self.initial_balance // self.charge_amount
        expected_final_balance = self.initial_balance - (
            expected_successful_charges * self.charge_amount
        )

        threads = []
        results = []

        for i in range(num_concurrent_requests):
            t = threading.Thread(
                target=self._charge_task,
                args=(
                    self.phone_number.id,
                    self.provider_account.id,
                    self.requester.user_id,
                    self.charge_amount,
                    results,
                ),
                name=f"ChargeThread-{i}",
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.provider_wallet.refresh_from_db()

        actual_successful_charges = results.count(True)
        actual_error_charges = len(
            [r for r in results if isinstance(r, str) and r.startswith("Error:")]
        )

        self.assertEqual(actual_successful_charges, expected_successful_charges)

        self.assertEqual(self.provider_wallet.balance, expected_final_balance)

        self.assertEqual(RequestCharge.objects.count(), expected_successful_charges)

        self.assertEqual(actual_error_charges, 0)
