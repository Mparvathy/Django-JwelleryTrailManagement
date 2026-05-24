from django.contrib import admin
from .models import customuser, Product, Wishlist, Cart, Category, Order, OrderItem

admin.site.register(customuser)
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Wishlist)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(OrderItem)