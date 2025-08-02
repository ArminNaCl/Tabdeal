import threading
import random
from django.test import TransactionTestCase, TestCase
from django.db import transaction, connection, connections
from django.db.models import F
from django.contrib.auth import get_user_model
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.test import TestCase
from accounts.models import RequestDeposit, RequestCharge, ProviderWallet
from django.db import transaction
import random
User = get_user_model()


from accounts.models import (
    ProviderAccount,
    ProviderWallet,
    ProviderAccountTeamMember,
    PhoneNumber,
    RequestCharge,
    RequestDeposit,
)
from django.utils.translation import gettext_lazy as _


class LargeScaleIntegrationTest(TestCase):
    def setUp(self):
        self.system_admin = User.objects.create(username="system_admin", is_staff=True)

        self.provider1_account = ProviderAccount.objects.create(name="Provider One")
        self.provider1_wallet = ProviderWallet.objects.create(
            account=self.provider1_account, balance=0
        )
        self.user_1_admin = User.objects.create(username="user_1_admin")
        self.provider1_requester_admin = ProviderAccountTeamMember.objects.create(
            user=self.user_1_admin,
            account=self.provider1_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.ADMIN,
        )
        self.user_1_staff = User.objects.create(username="user_1_staff")
        self.provider1_requester_staff = ProviderAccountTeamMember.objects.create(
            user=self.user_1_staff,
            account=self.provider1_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.STAFF,
        )
        self.user_1_user = User.objects.create(username="user_1_user")
        self.provider1_requester_user = ProviderAccountTeamMember.objects.create(
            user=self.user_1_user,
            account=self.provider1_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.USER,
        )

        self.provider2_account = ProviderAccount.objects.create(name="Provider Two")
        self.provider2_wallet = ProviderWallet.objects.create(
            account=self.provider2_account, balance=0
        )
        self.user_2_admin = User.objects.create(username="user_2_admin")
        self.provider2_requester_admin = ProviderAccountTeamMember.objects.create(
            user=self.user_2_admin,
            account=self.provider2_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.ADMIN,
        )
        self.user_2_staff = User.objects.create(username="user_2_staff")
        self.provider2_requester_staff = ProviderAccountTeamMember.objects.create(
            user=self.user_2_staff,
            account=self.provider2_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.STAFF,
        )
        self.user_2_user = User.objects.create(username="user_2_user")
        self.provider2_requester_user = ProviderAccountTeamMember.objects.create(
            user=self.user_2_user,
            account=self.provider2_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.USER,
        )

        self.phone_numbers = [
            PhoneNumber.objects.create(number=f"0{9222222200 + i}") for i in range(20)
        ]

        self.deposit_amount_per_request = 100000
        self.charge_amount_per_request = 100

    def test_deposit_then_drain_with_charges(self):
        deposit_amount = self.deposit_amount_per_request  # 10000
        charge_amount = self.charge_amount_per_request  # 100
        total_expected_charges = 0

        users1 = [self.user_1_admin, self.user_1_staff]
        users2 = [self.user_2_admin, self.user_2_staff]


        phone_ids = [pn.id for pn in self.phone_numbers]
        phone_count = len(phone_ids)
        phone_index = 0
        user_index = 0

        for deposit_round in range(5):  # 10 deposits
            # Step 1: Deposit
            deposit1 = RequestDeposit.objects.create(
                requester=self.provider1_requester_admin,
                amount=deposit_amount,
                account=self.provider1_account,
                status=RequestDeposit.Status.OPEN,
                assignee=self.system_admin,
            )
            deposit1.status = RequestDeposit.Status.APPROVED
            deposit1.save()
            
            deposit2 = RequestDeposit.objects.create(
                requester=self.provider2_requester_admin,
                amount=deposit_amount,
                account=self.provider2_account,
                status=RequestDeposit.Status.OPEN,
                assignee=self.system_admin,
            )
            deposit2.status = RequestDeposit.Status.APPROVED
            deposit2.save()

            self.provider1_wallet.refresh_from_db()
            self.provider2_wallet.refresh_from_db()
            before_charge_balance1 = self.provider1_wallet.balance
            before_charge_balance2 = self.provider2_wallet.balance
            charges_this_round1 = 0
            charges_this_round2 = 0

            # Step 2: Charge until wallet runs out
            while True:
                self.provider1_wallet.refresh_from_db()
                self.provider2_wallet.refresh_from_db()
                if (
                    self.provider1_wallet.balance < charge_amount
                    or self.provider1_wallet.balance < charge_amount
                    or random.random() > 0.12
                ):
                    break

                user1 = users1[user_index % len(users1)]
                user2 = users2[user_index % len(users2)]
                phone_number_id1 = phone_ids[phone_index % phone_count]
                phone_number_id2 = phone_ids[phone_index % phone_count]

                RequestCharge.create_charge_safely(
                    phone_number_id=phone_number_id1,
                    provider_account_id=self.provider1_account.id,
                    user_id=user1.id,
                    amount=charge_amount,
                )
                RequestCharge.create_charge_safely(
                    phone_number_id=phone_number_id2,
                    provider_account_id=self.provider2_account.id,
                    user_id=user2.id,
                    amount=charge_amount,
                )

                charges_this_round1 += 1
                charges_this_round2 += 1
                total_expected_charges += 2
                user_index += 1
                phone_index += 1

            # Step 3: Assert wallet is drained correctly
            self.provider1_wallet.refresh_from_db()
            self.provider2_wallet.refresh_from_db()
            expected_balance1 = before_charge_balance1 - (
                charges_this_round1 * charge_amount
            )
            expected_balance2 = before_charge_balance2 - (
                charges_this_round2 * charge_amount
            )
            self.assertEqual(self.provider1_wallet.balance, expected_balance1)
            self.assertEqual(self.provider2_wallet.balance, expected_balance2)

        # Step 4: Final assertions after all rounds
        self.assertEqual(RequestDeposit.objects.count(), 10)
        self.assertEqual(RequestCharge.objects.count(), total_expected_charges)

        expected_total_spent = total_expected_charges * charge_amount /2
        expected_final_balance = (5 * deposit_amount) - expected_total_spent

        self.provider1_wallet.refresh_from_db()
        self.assertEqual(self.provider1_wallet.balance, expected_final_balance)
        self.assertEqual(self.provider2_wallet.balance, expected_final_balance)


