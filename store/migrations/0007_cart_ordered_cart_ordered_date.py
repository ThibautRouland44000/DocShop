# Generated by Django 4.1.5 on 2023-01-23 15:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_product_stripe_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='ordered',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='cart',
            name='ordered_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
