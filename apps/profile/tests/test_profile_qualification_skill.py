from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.profile.models import StaffProfile, StaffProfileQualification, StaffProfileSkill
from apps.profile.tests.utils_master import create_test_qualification, create_test_skill
from datetime import date

User = get_user_model()

class StaffProfileQualificationSkillTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.profile = StaffProfile.objects.create(user=self.user, name_last='山田', name_first='太郎')
        self.qualification_master = create_test_qualification()
        self.skill_master = create_test_skill()

    def test_qualification_create(self):
        q = StaffProfileQualification.objects.create(
            staff_profile=self.profile,
            qualification=self.qualification_master,
            acquired_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
            certificate_number='ABC123',
            memo='メモ',
            score=900
        )
        self.assertEqual(q.staff_profile, self.profile)
        self.assertEqual(q.qualification, self.qualification_master)
        self.assertEqual(q.score, 900)

    def test_skill_create(self):
        s = StaffProfileSkill.objects.create(
            staff_profile=self.profile,
            skill=self.skill_master,
            acquired_date=date(2021, 2, 2),
            years_of_experience=5,
            memo='技能メモ'
        )
        self.assertEqual(s.staff_profile, self.profile)
        self.assertEqual(s.skill, self.skill_master)
        self.assertEqual(s.years_of_experience, 5)

    def test_qualification_unique_constraint(self):
        StaffProfileQualification.objects.create(
            staff_profile=self.profile,
            qualification=self.qualification_master
        )
        with self.assertRaises(Exception):
            StaffProfileQualification.objects.create(
                staff_profile=self.profile,
                qualification=self.qualification_master
            )

    def test_skill_unique_constraint(self):
        StaffProfileSkill.objects.create(
            staff_profile=self.profile,
            skill=self.skill_master
        )
        with self.assertRaises(Exception):
            StaffProfileSkill.objects.create(
                staff_profile=self.profile,
                skill=self.skill_master
            )
