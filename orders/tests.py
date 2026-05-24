# Create your tests here.
from django.test import TestCase
from django.contrib.auth.models import User

from products.models import Product
from warehouses.models import Warehouse
from inventory.models import Inventory


class OrderTestCase(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username='john',
            password='john123'
        )

        self.product = Product.objects.create(
            name='Phone',
            sku='PHN001',
            category='Electronics',
            price=500
        )

        self.warehouse = Warehouse.objects.create(
            name='Main Warehouse',
            location='Kathmandu'
        )

        self.inventory = Inventory.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=10
        )

    def test_inventory_created(self):

        self.assertEqual(
            self.inventory.quantity,
            10
        )