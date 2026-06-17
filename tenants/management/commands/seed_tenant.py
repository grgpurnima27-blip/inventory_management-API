from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds one tenant with products, warehouses, inventory, coupons, orders, and reviews for Swagger testing.'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('  SEEDING TENANT DATA')
        self.stdout.write('=' * 60 + '\n')

        try:
            with transaction.atomic():
                tenant     = self._seed_tenant()
                customer   = self._seed_customer()
                warehouses = self._seed_warehouses(tenant)
                products   = self._seed_products(tenant)
                self._seed_inventory(tenant, products, warehouses)
                self._seed_coupons(tenant)
                self._seed_order(tenant, customer, products, warehouses)
                self._seed_review(tenant, customer, products)
                self._seed_wishlist(customer, products)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'\nError during seeding: {e}'))
            raise

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('  SEEDING COMPLETE'))
        self.stdout.write('=' * 60)
        self.stdout.write('\n SWAGGER TESTING CREDENTIALS')
        self.stdout.write('-' * 40)
        self.stdout.write(f'  Vendor Admin  username : techmart_admin')
        self.stdout.write(f'  Vendor Admin  password : Admin@1234')
        self.stdout.write(f'  Customer      username : test_customer')
        self.stdout.write(f'  Customer      password : Customer@1234')
        self.stdout.write('\n TENANT HEADER FOR ALL REQUESTS')
        self.stdout.write('-' * 40)
        self.stdout.write(f'  X-Tenant-Slug: techmart')
        self.stdout.write('\n HOW TO USE SWAGGER')
        self.stdout.write('-' * 40)
        self.stdout.write('  1. Go to http://localhost:8000/swagger/')
        self.stdout.write('  2. POST /api/auth/login/  ->  get access token')
        self.stdout.write('  3. Click Authorize -> paste:  Bearer <access_token>')
        self.stdout.write('  4. Add header  X-Tenant-Slug: techmart  to requests')
        self.stdout.write('=' * 60 + '\n')

    # ── Tenant & Users ──────────────────────────────────────────────

    def _seed_tenant(self):
        from tenants.models import Tenant
        from accounts.models import Profile

        vendor_admin, created = User.objects.get_or_create(
            username='techmart_admin',
            defaults={
                'email': 'admin@techmart.com',
                'role': 'admin',
                'is_email_verified': True,
            }
        )
        if created:
            vendor_admin.set_password('Admin@1234')
            vendor_admin.save()
            Profile.objects.get_or_create(user=vendor_admin)
            self.stdout.write(self.style.SUCCESS('  [+] Vendor admin created: techmart_admin'))
        else:
            self.stdout.write('  [=] Vendor admin already exists: techmart_admin')

        tenant, created = Tenant.objects.get_or_create(
            slug='techmart',
            defaults={
                'name': 'TechMart Nepal',
                'description': 'Best electronics store in Nepal.',
                'owner': vendor_admin,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  [+] Tenant created: TechMart Nepal (slug=techmart)'))
        else:
            self.stdout.write('  [=] Tenant already exists: TechMart Nepal')

        return tenant

    def _seed_customer(self):
        from accounts.models import Profile

        customer, created = User.objects.get_or_create(
            username='test_customer',
            defaults={
                'email': 'customer@test.com',
                'role': 'customer',
                'is_email_verified': True,
            }
        )
        if created:
            customer.set_password('Customer@1234')
            customer.save()
            Profile.objects.get_or_create(user=customer, defaults={'city': 'Kathmandu'})
            self.stdout.write(self.style.SUCCESS('  [+] Customer created: test_customer'))
        else:
            self.stdout.write('  [=] Customer already exists: test_customer')

        return customer

    # ── Warehouses ──────────────────────────────────────────────────

    def _seed_warehouses(self, tenant):
        from warehouses.models import Warehouse

        warehouse_data = [
            {
                'name': 'TechMart Kathmandu',
                'city': 'Kathmandu',
                'location': 'New Road, Kathmandu',
                'latitude': Decimal('27.700769'),
                'longitude': Decimal('85.314940'),
            },
            {
                'name': 'TechMart Pokhara',
                'city': 'Pokhara',
                'location': 'Lakeside, Pokhara',
                'latitude': Decimal('28.209543'),
                'longitude': Decimal('83.990914'),
            },
        ]

        warehouses = []
        for data in warehouse_data:
            wh, created = Warehouse.objects.get_or_create(
                tenant=tenant,
                name=data['name'],
                defaults=data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [+] Warehouse: {wh.name}'))
            else:
                self.stdout.write(f'  [=] Warehouse exists: {wh.name}')
            warehouses.append(wh)

        return warehouses

    # ── Products ────────────────────────────────────────────────────

    def _seed_products(self, tenant):
        from products.models import Product

        product_data = [
            {'name': 'Dell Inspiron 15',    'sku': 'DELL-INS-15',  'category': 'Laptops',      'price': Decimal('85000.00')},
            {'name': 'Samsung Galaxy S24',  'sku': 'SAM-S24-BLK',  'category': 'Smartphones',  'price': Decimal('120000.00')},
            {'name': 'Sony WH-1000XM5',     'sku': 'SONY-WH-XM5',  'category': 'Audio',        'price': Decimal('45000.00')},
        ]

        products = []
        for data in product_data:
            p, created = Product.objects.get_or_create(
                tenant=tenant,
                sku=data['sku'],
                defaults={**data, 'tenant': tenant},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [+] Product: {p.name}  (SKU: {p.sku})'))
            else:
                self.stdout.write(f'  [=] Product exists: {p.name}')
            products.append(p)

        return products

    # ── Inventory ───────────────────────────────────────────────────

    def _seed_inventory(self, tenant, products, warehouses):
        from inventory.models import Inventory

        ktm, pkr = warehouses[0], warehouses[1]

        stock = [
            (products[0], ktm, 20),
            (products[0], pkr, 10),
            (products[1], ktm, 15),
            (products[1], pkr,  5),
            (products[2], ktm, 30),
            (products[2], pkr,  8),
        ]

        for product, warehouse, qty in stock:
            inv, created = Inventory.objects.get_or_create(
                tenant=tenant,
                product=product,
                warehouse=warehouse,
                defaults={'quantity': qty},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'  [+] Inventory: {product.name} @ {warehouse.name} = {qty}'
                ))
            else:
                self.stdout.write(
                    f'  [=] Inventory exists: {product.name} @ {warehouse.name}'
                )

    # ── Coupons ─────────────────────────────────────────────────────

    def _seed_coupons(self, tenant):
        from coupons.models import Coupon

        coupon_data = [
            {
                'code': 'SAVE10',
                'discount_type': Coupon.TYPE_PERCENTAGE,
                'discount_value': Decimal('10.00'),
                'minimum_order_amount': Decimal('1000.00'),
                'max_uses': 100,
                'is_active': True,
            },
            {
                'code': 'FLAT500',
                'discount_type': Coupon.TYPE_FIXED,
                'discount_value': Decimal('500.00'),
                'minimum_order_amount': Decimal('2000.00'),
                'max_uses': 50,
                'is_active': True,
            },
        ]

        for data in coupon_data:
            c, created = Coupon.objects.get_or_create(
                tenant=tenant,
                code=data['code'],
                defaults=data,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'  [+] Coupon: {c.code}  ({c.discount_type} - {c.discount_value})'
                ))
            else:
                self.stdout.write(f'  [=] Coupon exists: {c.code}')

    # ── Order ───────────────────────────────────────────────────────

    def _seed_order(self, tenant, customer, products, warehouses):
        from orders.models import Order, OrderItem
        from inventory.models import Inventory

        if Order.objects.filter(tenant=tenant, user=customer).exists():
            self.stdout.write('  [=] Order already exists for test_customer')
            return Order.objects.filter(tenant=tenant, user=customer).first()

        product   = products[0]  # Dell Inspiron
        warehouse = warehouses[0]  # Kathmandu
        qty       = 1
        unit_price = product.price
        total      = unit_price * qty

        order = Order.objects.create(
            tenant          = tenant,
            user            = customer,
            customer_name   = 'Test Customer',
            delivery_city   = 'Kathmandu',
            payment_method  = Order.PAYMENT_METHOD_COD,
            payment_status  = Order.PAYMENT_STATUS_PENDING,
            status          = Order.STATUS_PENDING,
            original_amount = total,
            discount_amount = Decimal('0.00'),
            total_price     = total,
        )

        OrderItem.objects.create(
            order      = order,
            product    = product,
            warehouse  = warehouse,
            quantity   = qty,
            unit_price = unit_price,
        )

        inv = Inventory.objects.get(tenant=tenant, product=product, warehouse=warehouse)
        inv.quantity -= qty
        inv.save()

        self.stdout.write(self.style.SUCCESS(
            f'  [+] Order #{order.id}: 1x {product.name} — NPR {total} (COD, pending)'
        ))
        return order

    # ── Reviews ─────────────────────────────────────────────────────

    def _seed_review(self, tenant, customer, products):
        from reviews.models import Review

        product = products[1]  # Samsung Galaxy
        review, created = Review.objects.get_or_create(
            tenant=tenant,
            user=customer,
            product=product,
            defaults={
                'rating': 5,
                'comment': 'Absolutely amazing phone! Very fast and great camera.',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f'  [+] Review: {customer.username} -> {product.name} (5*)'
            ))
        else:
            self.stdout.write(f'  [=] Review exists: {customer.username} -> {product.name}')

    # ── Wishlist ────────────────────────────────────────────────────

    def _seed_wishlist(self, customer, products):
        from wishlist.models import Wishlist

        for product in products[1:]:  # Samsung + Sony
            w, created = Wishlist.objects.get_or_create(
                user=customer,
                product=product,
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [+] Wishlist: {product.name}'))
            else:
                self.stdout.write(f'  [=] Wishlist exists: {product.name}')
