from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from main_app.models import UserDetail


class ModelsTestCase(TestCase):
    """ Testing UserDetail model works """
    user_creds = {
        'username': str(datetime.now()),
        'password': '',
        'first_name': 'test_first_name',
        'phone': '89001234567',
        'telegram': '@nickname'
    }

    @classmethod
    def setUpTestData(cls):
        test_user = User.objects.create(
            username=cls.user_creds['username'],
            password=cls.user_creds['password'],
            first_name=cls.user_creds['first_name']
        )
        test_user_details = UserDetail()
        test_user_details.user = test_user
        test_user_details.phone = cls.user_creds['phone']
        test_user_details.telegram = cls.user_creds['telegram']
        test_user_details.save()

    def test_url(self):
        """ Url is correct """
        user = UserDetail.objects.get(
            phone=self.user_creds['phone'],
            telegram=self.user_creds['telegram'],
        ).user
        path = reverse('student_detail_AP_url', kwargs={'pk': user.pk})
        url = user.details.get_absolute_url()
        self.assertEqual(path, url)
