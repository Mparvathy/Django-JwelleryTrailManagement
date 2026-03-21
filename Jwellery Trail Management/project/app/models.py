from django.db import models
from django.contrib.auth.models import User
from  django.contrib.auth.models import AbstractUser
from django.utils import timezone


class customuser(AbstractUser):
    phone = models.CharField(max_length=15, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    is_user = models.BooleanField(default=False)
    def has_admin_permission(self):
        return self.is_admin


# ── CATEGORY ─────────────────────────────────────────────────

class Category(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


# ── PRODUCT ──────────────────────────────────────────────────
class Product(models.Model):
    category    = models.ForeignKey(
                    Category,
                    on_delete=models.CASCADE,
                    related_name='products'
                  )
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    stock       = models.PositiveIntegerField(default=0)
    image       = models.ImageField(upload_to='products/')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def is_in_stock(self):
        return self.stock > 0


# ── CART ─────────────────────────────────────────────────────
class Cart(models.Model):
    user     = models.ForeignKey(customuser, on_delete=models.CASCADE, related_name='cart_items')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} — {self.product.name} x{self.quantity}"

    def subtotal(self):
        return self.product.price * self.quantity