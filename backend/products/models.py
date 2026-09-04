from django.db import models
import uuid
from django.utils.text import slugify
from categories.models import Category

class Tag(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100,unique=True)
    slug=models.SlugField(unique=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def save(self,*args,**kwargs):
        self.slug=slugify(self.name)
        super().save(self,*args,**kwargs)

    def __str__(self):
        return self.name
    
class Product(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    name=models.CharField(max_length=100)
    category=models.ForeignKey(Category,on_delete=models.PROTECT,related_name='products')
    tags=models.ManyToManyField(Tag,related_name="products",blank=True)
    description=models.TextField(blank=True)
    price=models.DecimalField(max_digits=10,decimal_places=2)
    stock=models.PositiveIntegerField(default=0)
    slug=models.SlugField(unique=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)



    def save(self,*args,**kwargs):
        self.slug=slugify(self.name)
        super().save(*args,**kwargs)

    def __str__(self):
        return self.name