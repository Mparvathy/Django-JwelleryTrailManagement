from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/', views.menu, name='menu'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('cart/remove/<int:cart_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:cart_id>/', views.update_cart, name='update_cart'),
    path('category/<str:category_name>/', views.category_products, name='category_products'),
    path('about/', views.about, name='about'),
    path('adminlogin/',     views.adminlogin,     name='adminlogin'),
    path('adminlogout/',    views.adminlogout,    name='adminlogout'),
    path('admindashboard/', views.admindashboard, name='admindashboard'),
    
    path('add-category/', views.add_category, name='admin_add_category'),
    path('manage-categories/',        views.manage_categories, name='admin_manage_categories'),
    path('edit-category/<int:pk>/',   views.edit_category,     name='admin_edit_category'),
    path('delete-category/<int:pk>/', views.delete_category,   name='admin_delete_category'),

    path('myadmin/add-product/',             views.add_product,    name='admin_add_product'),
    path('manage-products/',         views.manage_products,name='admin_manage_products'),
    path('admin-orders/', views.admin_orders, name='admin_orders'),
    path('admin-users/', views.admin_users, name='admin_users'),
    path('edit-product/<int:pk>/',   views.edit_product,   name='admin_edit_product'),
    path('delete-product/<int:pk>/', views.delete_product, name='admin_delete_product'),
    path('admin-print-orders/', views.print_all_orders, name='admin_print_orders'),
    path('admin-orders/update/<int:order_id>/', views.update_order_status, name='update_order_status'),

    path('tryon/',                           views.tryon,        name='tryon'), 
    path('tryon/stop/',                      views.tryon_stop,   name='tryon_stop'),      
    path('tryon/stream/<int:product_id>/',   views.tryon_stream, name='tryon_stream'),   
     
     path('register/', views.register, name='register'),
     path('verify-otp/', views.verify_otp, name='verify_otp'),
     path('login/',  views.userlogin,  name='userlogin'),
     path('dashboard/', views.userdashboard, name='userdashboard'),
     path('logout/', views.userlogout, name='userlogout'),
     path('wishlist/', views.wishlist, name='wishlist'),
     path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
     path('profile/', views.profile, name='profile'),
     path('checkout/', views.checkout, name='checkout'),
     path('process-payment/', views.process_payment, name='process_payment'),
     path('order-success/<int:order_id>/', views.order_success, name='order_success'),
     path('my-orders/', views.my_orders, name='my_orders'),
     path('my-orders/<int:order_id>/', views.order_details, name='order_details'),
     path('my-orders/<int:order_id>/invoice/', views.download_invoice, name='download_invoice'),


  ]
