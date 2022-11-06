""" These tests verify pages are loading correctly """

from django.test.testcases import TestCase

from main_app.models import UserDetail, User


class TestPagesLoadsByAnonymousUser(TestCase):
    """ These tests check proper loading of all pages access
    to which anonymous user has access """

    # pages for anonymous user
    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_register_page(self):
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

    def test_logout_page(self):
        response = self.client.get('/logout')
        self.assertRedirects(response, '/')

    def test_info_page(self):
        response = self.client.get('/info')
        self.assertEqual(response.status_code, 200)

    # pages for authenticated users
    def test_lessons_page_for_user(self):
        response = self.client.get('/my-lessons')
        self.assertRedirects(response, '/login?next=/my-lessons')

    def test_add_lesson_page_for_user(self):
        response = self.client.get('/add-lesson')
        self.assertRedirects(response, '/login?next=/add-lesson')

    # pages for admin
    def test_admin_page_for_admin(self):
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 301)
        response = self.client.get('/admin', follow=True)
        self.assertRedirects(response, '/admin/login/?next=/admin/',
                             status_code=301)

    def test_settings_page_for_admin(self):
        response = self.client.get('/admin-panel/settings')
        self.assertRedirects(response, '/')

    def test_add_lesson_page_for_admin(self):
        response = self.client.get('/admin-panel/add-lesson')
        self.assertRedirects(response, '/')

    def test_time_block_page_for_admin(self):
        response = self.client.get('/admin-panel/block-time')
        self.assertRedirects(response, '/')

    def test_students_page_for_admin(self):
        response = self.client.get('/admin-panel/students')
        self.assertRedirects(response, '/')

    def test_student_page_for_admin(self):
        # creating user
        user = User()
        userdetail = UserDetail()
        user.first_name = 'user1'
        userdetail.user = user
        userdetail.phone = '89121234567'
        userdetail.telegram = '@nickname'
        user.save()
        userdetail.save()

        response = self.client.get(f'/admin-panel/students/{user.pk}')
        self.assertRedirects(response, '/')


class TestPagesLoadsByAuthenticatedUser(TestCase):
    """ These tests check proper loading of all pages access
    to which authenticated user has access """

    user_credentials = {
        'first_name': 'test_user_name',
        'phone': '89121324657',
        'telegram': '@nickname'
    }

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(
            first_name=cls.user_credentials['first_name'])
        UserDetail.objects.create(
            user=user,
            phone=cls.user_credentials['phone'],
            telegram=cls.user_credentials['telegram']
        )

    def setUp(self):
        user = User.objects.get(details__phone=self.user_credentials['phone'])
        self.client._login(user)

    # pages for anonymous user
    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_register_page(self):
        response = self.client.get('/register')
        self.assertRedirects(response, '/')

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertRedirects(response, '/')

    def test_logout_page(self):
        response = self.client.get('/logout')
        self.assertRedirects(response, '/')

    def test_info_page(self):
        response = self.client.get('/info')
        self.assertEqual(response.status_code, 200)

    # pages for authenticated users
    def test_lessons_page_for_user(self):
        response = self.client.get('/my-lessons')
        self.assertEqual(response.status_code, 200)

    def test_add_lesson_page_for_user(self):
        response = self.client.get('/add-lesson')
        self.assertEqual(response.status_code, 200)

    # pages for admin
    def test_admin_page_for_admin(self):
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 301)
        response = self.client.get('/admin', follow=True)
        self.assertRedirects(response, '/admin/login/?next=/admin/',
                             status_code=301)

    def test_settings_page_for_admin(self):
        response = self.client.get('/admin-panel/settings')
        self.assertRedirects(response, '/')

    def test_add_lesson_page_for_admin(self):
        response = self.client.get('/admin-panel/add-lesson')
        self.assertRedirects(response, '/')

    def test_time_block_page_for_admin(self):
        response = self.client.get('/admin-panel/block-time')
        self.assertRedirects(response, '/')

    def test_students_page_for_admin(self):
        response = self.client.get('/admin-panel/students')
        self.assertRedirects(response, '/')

    def test_student_page_for_admin(self):
        # creating user
        user = User()
        userdetail = UserDetail()
        user.first_name = 'user1'
        user.username = user.date_joined
        userdetail.user = user
        userdetail.phone = '89121234567'
        userdetail.telegram = '@nickname'
        user.save()
        userdetail.save()

        response = self.client.get(f'/admin-panel/students/{user.pk}')
        self.assertRedirects(response, '/')


class TestPagesLoadsByAdmin(TestCase):
    """ These tests check proper loading of all pages access
    to which admin user has access """

    admin_credentials = {
        'username': 'test_admin',
        'password': 'test_admin_pass'
    }

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(is_staff=True, is_superuser=True,
                                 **cls.admin_credentials)

    def setUp(self):
        self.client.login(**self.admin_credentials)

    # pages for anonymous user
    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_register_page(self):
        response = self.client.get('/register')
        self.assertRedirects(response, '/')

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertRedirects(response, '/')

    def test_logout_page(self):
        response = self.client.get('/logout')
        self.assertRedirects(response, '/')

    def test_info_page(self):
        response = self.client.get('/info')
        self.assertEqual(response.status_code, 200)

    # pages for authenticated users
    def test_lessons_page_for_user(self):
        response = self.client.get('/my-lessons')
        self.assertRedirects(response, '/')

    def test_add_lesson_page_for_user(self):
        response = self.client.get('/add-lesson')
        self.assertRedirects(response, '/admin-panel/add-lesson')

    # pages for admin
    def test_admin_page_for_admin(self):
        response = self.client.get('/admin')
        self.assertRedirects(response, '/admin/', status_code=301)

    def test_settings_page_for_admin(self):
        response = self.client.get('/admin-panel/settings')
        self.assertEqual(response.status_code, 200)

    def test_add_lesson_page_for_admin(self):
        response = self.client.get('/admin-panel/add-lesson')
        self.assertEqual(response.status_code, 200)

    def test_time_block_page_for_admin(self):
        response = self.client.get('/admin-panel/block-time')
        self.assertEqual(response.status_code, 200)

    def test_students_page_for_admin(self):
        response = self.client.get('/admin-panel/students')
        self.assertEqual(response.status_code, 200)

    def test_student_page_for_admin(self):
        any_username = 'user1'
        any_password = 'pass1'
        user = User.objects.create_user(
            username=any_username,
            password=any_password
        )
        UserDetail.objects.create(user=user)
        response = self.client.get(f'/admin-panel/students/{user.pk}')
        self.assertEqual(response.status_code, 200)
