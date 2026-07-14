from rest_framework import serializers
from .models import Product
import cloudinary.uploader


class ProductReadSerializer(serializers.ModelSerializer):
    """Public - everyone can see including image"""
    # Replace image field with full URL
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'sku',
            'category',
            'price',
            'quantity',
            'image',  # it will return full Cloudinary URL
            'created_at',
            'updated_at',
            'requires_prescription',
        ]
    
    def get_image(self, obj):
        """Return full Cloudinary URL for the image"""
        if obj.image:
            return obj.image.url  # it returns complete Cloudinary URL
        return None


class ProductWriteSerializer(serializers.ModelSerializer):
    """Admin only - create/update with image upload"""
    
    image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Product image file (JPEG, PNG, WebP, max 2MB)"
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'sku',
            'category',
            'price',
            'image',
            'quantity',
        ]

    def validate_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                'Product name must contain at least 3 characters.'
            )
        return value

    def validate_category(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError(
                'Category name is too short.'
            )
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'Price must be greater than zero.'
            )
        return value

    def validate_sku(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                'SKU must contain at least 3 characters.'
            )
        # Check for uniqueness with tenant
        tenant = self.context.get('request').tenant if self.context.get('request') else None
        if tenant:
            if Product.objects.filter(tenant=tenant, sku=value).exists():
                if self.instance:
                    if self.instance.sku != value:
                        raise serializers.ValidationError(
                            'Product with this SKU already exists in your tenant.'
                        )
                else:
                    raise serializers.ValidationError(
                        'Product with this SKU already exists in your tenant.'
                    )
        return value

    def validate_image(self, value):
        """Validate image file size and type"""
        if value:
            # Check file size (max 2MB)
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError(
                    'Image size must not exceed 2MB.'
                )
            
            # Check file type
            allowed = ['image/jpeg', 'image/png', 'image/webp']
            if value.content_type not in allowed:
                raise serializers.ValidationError(
                    'Only JPEG, PNG, and WebP images are allowed.'
                )
        return value

    def create(self, validated_data):
        """Handle image upload to Cloudinary on creation"""
        image = validated_data.pop('image', None)
        product = Product.objects.create(**validated_data)
        
        if image:
            try:
                result = cloudinary.uploader.upload(
                    image,
                    folder='products/',
                    public_id=f'product_{product.id}',
                    overwrite=True,
                )
                product.image = result['public_id']
                product.save(update_fields=['image'])
                print(f"Image uploaded successfully: {result['secure_url']}")
            except Exception as e:
                # Log error but don't fail the creation
                print(f"Cloudinary upload error: {e}")
        
        return product

    def update(self, instance, validated_data):
        """Handle image upload to Cloudinary on update"""
        image = validated_data.pop('image', None)
        
        # Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle image upload
        if image:
            try:
                result = cloudinary.uploader.upload(
                    image,
                    folder='products/',
                    public_id=f'product_{instance.id}',
                    overwrite=True,
                )
                instance.image = result['public_id']
                print(f"Image updated successfully: {result['secure_url']}")
            except Exception as e:
                print(f"Cloudinary upload error: {e}")
        
        instance.save()
        return instance