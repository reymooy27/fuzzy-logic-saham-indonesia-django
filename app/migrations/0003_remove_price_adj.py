# Generated by Django 4.2.4 on 2023-08-13 13:34

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0002_price_code"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="price",
            name="adj",
        ),
    ]
