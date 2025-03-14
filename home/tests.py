from django.test import TestCase
from django.urls import reverse

class HomePageTests(TestCase):
    def test_home_page_status_code(self):
        response = self.client.get(reverse('home:index'))
        self.assertEqual(response.status_code, 200)

    def test_home_page_template_used(self):
        response = self.client.get(reverse('home:index'))
        self.assertTemplateUsed(response, 'home/index.html')