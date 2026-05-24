from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Wishlist
import os

@receiver(post_save, sender=Wishlist)
def wishlist_added_notification(sender, instance, created, **kwargs):
    if created:
        user = instance.user
        product = instance.product
        if user.email:
            subject = f"Added to Wishlist: {product.name}"
            context = {
                'user': user,
                'product': product,
            }
            html_message = render_to_string('emails/wishlist_added.html', context)
            plain_message = strip_tags(html_message)
            email = EmailMultiAlternatives(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email]
            )
            email.attach_alternative(html_message, "text/html")
            if product.image:
                try:
                    img_path = product.image.path
                    with open(img_path, 'rb') as f:
                        from email.mime.image import MIMEImage
                        msg_img = MIMEImage(f.read())
                        msg_img.add_header('Content-ID', '<product_image>')
                        email.attach(msg_img)
                except Exception as e:
                    print(f"Error attaching image: {e}")
            email.send(fail_silently=True)
