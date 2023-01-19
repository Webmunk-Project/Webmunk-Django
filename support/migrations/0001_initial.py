# pylint: skip-file
# Generated by Django 3.2.16 on 2022-11-28 23:52

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AmazonASINItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asin', models.CharField(max_length=1024, unique=True)),
                ('name', models.CharField(blank=True, max_length=1024, null=True)),
                ('category', models.CharField(blank=True, max_length=1024, null=True)),
                ('added', models.DateTimeField()),
                ('updated', models.DateTimeField()),
            ],
        ),
    ]