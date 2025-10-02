from rest_framework.test import APITestCase
from store.models import Product, Category

class ProductAPITest(APITestCase):
    def setUp(self):
        c = Category.objects.create(name="Qikink Products")
        Product.objects.create(name="p1", sku="S1", price=10, category=c, dealer="Qikink")
    def test_list_products(self):
        res = self.client.get("/api/products/")
        assert res.status_code == 200
        assert res.json()["results"][0]["sku"] == "S1"
