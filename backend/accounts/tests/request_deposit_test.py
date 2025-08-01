from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


from accounts.models import (
    RequestDeposit,
    ProviderAccountTeamMember,
    ProviderAccount,
    ProviderWallet,
)


User = get_user_model()


class RequestDepositModelTest(TestCase):

    def setUp(self):
        self.staff_user = User.objects.create(username="staffuser", is_staff=True)
        self.requester_user = User.objects.create(username="requesteruser")
        self.provider_account = ProviderAccount.objects.create(
            name="Test Provider Account"
        )
        self.provider_wallet = ProviderWallet.objects.create(
            account=self.provider_account
        )
        self.requester_team_member = ProviderAccountTeamMember.objects.create(
            user=self.requester_user,
            account=self.provider_account,
            permission_level=ProviderAccountTeamMember.PermissionLevel.ADMIN,
        )

    def test_is_finalized(self):
        open_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=100,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.OPEN,
        )

        approved_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=200,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.APPROVED,
        )

        rejected_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=300,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.REJECTED,
        )

        self.assertFalse(
            open_request.is_finalized(), "Open request should not be finalized."
        )
        self.assertTrue(
            approved_request.is_finalized(), "Approved request should be finalized."
        )
        self.assertTrue(
            rejected_request.is_finalized(), "Rejected request should be finalized."
        )

    def test_clean_sets_assignee(self):

        request = RequestDeposit(
            requester=self.requester_team_member,
            amount=100,
            account=self.provider_account,
            status=RequestDeposit.Status.OPEN,
        )
        request.clean()

        self.assertEqual(
            request.assignee, self.staff_user, "clean() should set the assignee."
        )

    def test_clean_prevents_change_on_finalized_request(self):

        approved_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=200,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.APPROVED,
        )

        approved_request.amount = 250
        with self.assertRaises(
            ValidationError,
            msg="clean() should prevent changes to an approved request.",
        ):
            approved_request.clean()

        rejected_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=300,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.REJECTED,
        )

        rejected_request.comment = "Updated comment"
        with self.assertRaises(
            ValidationError, msg="clean() should prevent changes to a rejected request."
        ):
            rejected_request.clean()

    def test_save_creates_new_request_and_assigns(self):

        request = RequestDeposit(
            requester=self.requester_team_member,
            amount=100,
            account=self.provider_account,
            status=RequestDeposit.Status.OPEN,
        )
        request.full_clean()
        request.save()

        self.assertIsNotNone(
            request.pk, "Request should have a primary key after saving."
        )
        self.assertEqual(
            request.status,
            RequestDeposit.Status.OPEN,
            "New request status should be OPEN.",
        )
        self.assertEqual(
            request.assignee, self.staff_user, "Assignee should be set on initial save."
        )

    def test_save_prevents_modification_of_finalized_request(self):

        approved_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=200,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.APPROVED,
        )
        approved_request.amount = 250
        with self.assertRaises(
            ValidationError,
            msg="save() should prevent modification of an approved request.",
        ):
            approved_request.save()

        rejected_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=300,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.REJECTED,
        )

        rejected_request.comment = "Another comment"
        with self.assertRaises(
            ValidationError,
            msg="save() should prevent modification of a rejected request.",
        ):
            rejected_request.save()

    def test_low_permission_team_member_request_deposit(self):
        low_permission_user = User.objects.create(username="low_permission_user")
        low_permission_team_member = ProviderAccountTeamMember.objects.create(
            account=self.provider_account,
            user=low_permission_user,
            permission_level=ProviderAccountTeamMember.PermissionLevel.STAFF,
        )
        with self.assertRaisesRegex(
            PermissionError,
            "The Requester user does not have permission to this action",
        ):
            RequestDeposit.objects.create(
                requester=low_permission_team_member,
                amount=200,
                account=self.provider_account,
                assignee=self.staff_user,
                status=RequestDeposit.Status.OPEN,
            )

    def test_save_approves_and_deposits(self):
        request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=100,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.OPEN,
        )

        request.status = RequestDeposit.Status.APPROVED
        request.save()

        self.assertEqual(
            request.status, RequestDeposit.Status.APPROVED, "Status should be APPROVED."
        )

    def test_delete_open_request(self):

        request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=100,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.OPEN,
        )
        request_id = request.id
        request.delete()

        self.assertFalse(
            RequestDeposit.objects.filter(id=request_id).exists(),
            "Open request should be deleted from the database.",
        )

    def test_delete_finalized_request_raises_error(self):
        """
        Tests that a finalized (approved or rejected) request cannot be deleted.
        """

        approved_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=200,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.APPROVED,
        )
        with self.assertRaises(
            ValidationError, msg="Should not be able to delete an approved request."
        ):
            approved_request.delete()

        rejected_request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=300,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.REJECTED,
        )
        with self.assertRaises(
            ValidationError, msg="Should not be able to delete a rejected request."
        ):
            rejected_request.delete()

    def test_save_rejects_and_does_not_deposit(self):
        request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=100,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.OPEN,
        )

        request.status = RequestDeposit.Status.REJECTED
        request.save()

        self.assertEqual(
            request.status, RequestDeposit.Status.REJECTED, "Status should be REJECTED."
        )

    def test_double_spending_prevention(self):

        request = RequestDeposit.objects.create(
            requester=self.requester_team_member,
            amount=100,
            account=self.provider_account,
            assignee=self.staff_user,
            status=RequestDeposit.Status.OPEN,
        )

        request.status = RequestDeposit.Status.APPROVED
        request.save()
        self.assertEqual(
            request.status,
            RequestDeposit.Status.APPROVED,
            "Status should be APPROVED after first save.",
        )

        with self.assertRaises(
            ValidationError,
            msg="Should not be able to change status of finalized request.",
        ):
            request.status = RequestDeposit.Status.OPEN
            request.save()
