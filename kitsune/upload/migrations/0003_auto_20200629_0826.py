# Generated by Django 2.2.13 on 2020-06-29 08:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('upload', '0002_auto_20180523_0517'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imageattachment',
            name='file',
            field=models.ImageField(max_length=250, upload_to='uploads/images/'),
        ),
        migrations.AlterField(
            model_name='imageattachment',
            name='thumbnail',
            field=models.ImageField(null=True, upload_to='uploads/images/thumbnails/'),
        ),
    ]