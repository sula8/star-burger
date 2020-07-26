# Generated by Django 3.0.7 on 2020-07-25 17:59

from django.db import migrations, models
import django.utils.datetime_safe


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0040_order_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='registered_at',
            field=models.DateTimeField(default=django.utils.datetime_safe.datetime.now, verbose_name='Дата создания заказа'),
        ),
    ]