from django.db import models
import uuid
from django.utils.text import slugify
class Category(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    parent=models.ForeignKey("self",on_delete=models.PROTECT,null=True,blank=True,related_name="children")

    name=models.CharField(max_length=100,unique=True)
    slug=models.SlugField(unique=True,blank=True)


    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def save(self,*args,**kwargs):
        self.slug=slugify(self.name)
        super().save(*args,**kwargs)
    def __str__(self):
        return self.name