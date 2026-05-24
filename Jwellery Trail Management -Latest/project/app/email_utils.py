from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_order_confirmation_email(order):
    if not order.user.email:
        return

    context = {
        'order': order,
        'user': order.user,
    }
    html_message = render_to_string('emails/order_placed.html', context)
    plain_message = strip_tags(html_message)
    email = EmailMultiAlternatives(
        subject=f'Order Placed Successfully - ORD-{order.id}',
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.user.email],
    )
    email.attach_alternative(html_message, 'text/html')
    email.send(fail_silently=True)


def send_order_status_email(order):
    if not order.user.email:
        return

    context = {
        'order': order,
        'user': order.user,
    }
    html_message = render_to_string('emails/order_status.html', context)
    plain_message = strip_tags(html_message)
    email = EmailMultiAlternatives(
        subject=f'Order Status Update - ORD-{order.id}',
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.user.email],
    )
    email.attach_alternative(html_message, 'text/html')
    email.send(fail_silently=True)
