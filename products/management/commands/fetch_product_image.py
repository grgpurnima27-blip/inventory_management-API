import requests
import cloudinary.uploader

from django.core.management.base import BaseCommand
from django.conf import settings

from products.models import Product


class Command(BaseCommand):
    help = 'Auto-fetch images from Pexels for all products without images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing images too',
        )

    def handle(self, *args, **options):
        overwrite = options['overwrite']

        if overwrite:
            products = Product.objects.all()
        else:
            products = Product.objects.filter(image='')

        if not products.exists():
            self.stdout.write(
                self.style.WARNING('No products need images.')
            )
            return

        total = products.count()
        success = 0
        failed = 0

        self.stdout.write(f'Found {total} products to process...\n')

        for product in products:
            self.stdout.write(f'Fetching image for: {product.name}...')

            headers = {'Authorization': settings.PEXELS_API_KEY}
            params = {'query': product.name, 'per_page': 1}

            try:
                response = requests.get(
                    'https://api.pexels.com/v1/search',
                    headers=headers,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                photos = data.get('photos', [])

                # Fallback to category if product name finds nothing
                if not photos:
                    params['query'] = product.category
                    response = requests.get(
                        'https://api.pexels.com/v1/search',
                        headers=headers,
                        params=params,
                        timeout=10
                    )
                    data = response.json()
                    photos = data.get('photos', [])

                if not photos:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  No image found for "{product.name}" '
                            f'or category "{product.category}" — skipping.'
                        )
                    )
                    failed += 1
                    continue

                image_url = photos[0]['src']['large']

                result = cloudinary.uploader.upload(
                    image_url,
                    folder='products/',
                    public_id=f'product_{product.id}',
                    overwrite=True,
                )

                product.image = result['public_id']
                product.save(update_fields=['image'])
                success += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f'  Done — {result["secure_url"]}'
                    )
                )

            except requests.RequestException as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  Pexels error for "{product.name}": {str(e)}'
                    )
                )
                failed += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  Error for "{product.name}": {str(e)}'
                    )
                )
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccess: {success} | Failed: {failed} | Total: {total}'
            )
        )