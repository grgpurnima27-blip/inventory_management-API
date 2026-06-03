from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.tokens import generate_token

User = get_user_model()


class EmailAuthTestCase(APITestCase):

    def setUp(self):
        self.username = "testuser"
        self.email = "testuser@example.com"
        self.password = "SecurePassword123"
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password,
            role="customer",
            is_email_verified=False
        )

    def test_registration_sends_verification_email(self):
        register_url = reverse("register")
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Password123!"
        }
        
        # Clear outbox
        mail.outbox = []
        
        response = self.client.post(register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify user is created and unverified
        new_user = User.objects.get(username="newuser")
        self.assertFalse(new_user.is_email_verified)
        
        # Verify verification email is sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ["newuser@example.com"])
        self.assertIn("Verify your Inventory Management API account", sent_email.subject)
        self.assertIn("/api/auth/verify-email/", sent_email.body)

    def test_email_verification_success(self):
        token = generate_token(self.user.id, "verify_email")
        verify_url = reverse("verify-email", kwargs={"token": token})
        
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("verified successfully", response.data["message"])
        
        # Reload user and check verification status
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_email_verification_invalid_token(self):
        verify_url = reverse("verify-email", kwargs={"token": "invalid_token_signature"})
        
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_login_unverified_email_fails(self):
        login_url = reverse("login")
        data = {
            "username": self.username,
            "password": self.password
        }
        
        response = self.client.post(login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email is not verified", response.data["non_field_errors"][0])

    def test_login_verified_email_succeeds(self):
        self.user.is_email_verified = True
        self.user.save()
        
        login_url = reverse("login")
        data = {
            "username": self.username,
            "password": self.password
        }
        
        response = self.client.post(login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_forgot_password_sends_email(self):
        forgot_url = reverse("forgot-password")
        data = {"email": self.email}
        
        # Clear outbox
        mail.outbox = []
        
        response = self.client.post(forgot_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("sent", response.data["message"])
        
        # Verify email is sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [self.email])
        self.assertIn("Reset your Inventory Management API password", sent_email.subject)
        self.assertIn("/api/auth/reset-password/", sent_email.body)

    def test_reset_password_success(self):
        token = generate_token(self.user.id, "reset_password")
        reset_url = reverse("reset-password", kwargs={"token": token})
        
        new_password = "NewSecurePassword123"
        data = {
            "password": new_password,
            "confirm_password": new_password
        }
        
        response = self.client.post(reset_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("successfully", response.data["message"])
        
        # Verify user can log in with new password
        self.user.refresh_from_db()
        self.user.is_email_verified = True
        self.user.save()
        
        login_url = reverse("login")
        login_data = {
            "username": self.username,
            "password": new_password
        }
        login_response = self.client.post(login_url, login_data)
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_reset_password_invalid_token(self):
        reset_url = reverse("reset-password", kwargs={"token": "invalid_token"})
        data = {
            "password": "NewSecurePassword123",
            "confirm_password": "NewSecurePassword123"
        }
        
        response = self.client.post(reset_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_reset_password_mismatched_passwords(self):
        token = generate_token(self.user.id, "reset_password")
        reset_url = reverse("reset-password", kwargs={"token": token})
        
        data = {
            "password": "NewSecurePassword123",
            "confirm_password": "DifferentPassword123"
        }
        
        response = self.client.post(reset_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)
