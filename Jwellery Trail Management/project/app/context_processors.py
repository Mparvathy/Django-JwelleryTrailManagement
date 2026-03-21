from .models import Cart

def cart_count(request):
    if request.user.is_authenticated and hasattr(request.user, 'is_user') and request.user.is_user:
        count = Cart.objects.filter(user=request.user).count()
    else:
        count = 0
    return {'cart_count': count}
