from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_order_shipping_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='admin_comment',
            field=models.TextField(blank=True, default=''),
        ),
    ]
