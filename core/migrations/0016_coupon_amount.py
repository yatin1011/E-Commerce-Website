# Generated by Django 2.2 on 2021-08-01 08:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_auto_20210731_1752'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='amount',
            field=models.FloatField(default=3),
            preserve_default=False,
        ),
    ]
