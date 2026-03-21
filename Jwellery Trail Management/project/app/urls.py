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
    path('edit-product/<int:pk>/',   views.edit_product,   name='admin_edit_product'),
    path('delete-product/<int:pk>/', views.delete_product, name='admin_delete_product'),

    path('tryon/',                           views.tryon,        name='tryon'), 
    path('tryon/stop/',                      views.tryon_stop,   name='tryon_stop'),      
    path('tryon/stream/<int:product_id>/',   views.tryon_stream, name='tryon_stream'),   
     
     path('register/', views.register, name='register'),
     path('login/',  views.userlogin,  name='userlogin'),
     path('dashboard/', views.userdashboard, name='userdashboard'),
     path('logout/', views.userlogout, name='userlogout'),


 ]
