from django.db import models
import uuid
from django.utils.text import slugify
from categories.models import Category
from django.core.exceptions import ValidationError

class Tag(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100,unique=True)
    slug=models.SlugField(unique=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def save(self,*args,**kwargs):
        self.slug=slugify(self.name)
        super().save(*args,**kwargs)

    def __str__(self):
        return self.name

class Brand(models.Model):
    name=models.CharField(max_length=100,unique=True)
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    slug=models.SlugField(unique=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    modified_at=models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.slug=slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return  self.name
class Product(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100)
    category=models.ForeignKey(Category,on_delete=models.PROTECT,related_name='products')
    tags=models.ManyToManyField(Tag,related_name="products",blank=True)
    description=models.TextField(blank=True)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    stock=models.PositiveIntegerField(default=0)
    brand=models.ForeignKey(Brand,on_delete=models.PROTECT,related_name="products",null=True,blank=True)
    slug=models.SlugField(unique=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def save(self,*args,**kwargs):
        self.slug=slugify(self.name)
        super().save(*args,**kwargs)

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="images")
    image=models.ImageField(upload_to="products/",blank=True)
    image_url=models.URLField(blank=True)
    is_primary=models.BooleanField(default=False)
    primary_product_key=models.GeneratedField(
        expression=models.Case(
            models.When(
                is_primary=True,
                then=models.F("product")
            ),
            default=models.Value(None),
            output_field=models.UUIDField(),
        ),
        output_field=models.UUIDField(),
        db_persist=True,
        null=True,editable=False
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    

    class Meta:
        constraints=[
            models.UniqueConstraint(
                fields=["primary_product_key"],
                name="unique_primary_image_per_product"
            )
        ]
    def clean(self):
        if not self.image and not self.image_url:
            raise ValidationError(
                "Please provide either an image or an image URL."
            )

    def __str__(self):
        return f"{self.product.name} - Image"
