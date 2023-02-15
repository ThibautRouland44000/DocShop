from django.test import TestCase
from django.urls import reverse

from store.models import Product


class StoreTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Sneakers Docstring",
            price=10,
            stock=10,
            description="De superbe sneakers"
        )

    def test_products_are_shown_on_index_page(self):
        resp = self.client.get(reverse("index"))

        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.product.name, str(resp.content))