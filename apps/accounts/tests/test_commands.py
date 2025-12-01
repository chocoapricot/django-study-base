import csv
import os
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

class ImportUsersCommandTest(TestCase):
    def setUp(self):
        self.csv_file_path = 'test_users.csv'

    def tearDown(self):
        if os.path.exists(self.csv_file_path):
            os.remove(self.csv_file_path)

    def test_import_users_command(self):
        """
        Test that users are imported correctly from a CSV file.
        """
        csv_data = [
            ['testuser1', 'password123', 'test1@example.com', 'User', 'Test'],
            ['testuser2', 'password456', 'test2@example.com', 'UserTwo', 'Test'],
        ]

        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

        # StringIO is used to capture the output of the command
        out = StringIO()
        call_command('import_users', self.csv_file_path, stdout=out)

        self.assertIn('Successfully created user "testuser1"', out.getvalue())
        self.assertIn('Successfully created user "testuser2"', out.getvalue())

        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(EmailAddress.objects.count(), 2)

        user1 = User.objects.get(username='testuser1')
        self.assertEqual(user1.email, 'test1@example.com')
        self.assertEqual(user1.last_name, 'User')
        self.assertEqual(user1.first_name, 'Test')
        self.assertTrue(user1.check_password('password123'))

        email1 = EmailAddress.objects.get(user=user1)
        self.assertTrue(email1.primary)
        self.assertTrue(email1.verified)
