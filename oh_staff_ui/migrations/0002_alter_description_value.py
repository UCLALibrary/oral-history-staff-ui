# Generated by Django 4.1.3 on 2023-04-05 23:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oh_staff_ui', '0001_0001_super_squash_everything'),
    ]

    operations = [
        migrations.AlterField(
            model_name='description',
            name='value',
            field=models.CharField(max_length=8000),
        ),
    ]
