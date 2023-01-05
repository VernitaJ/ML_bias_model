# Generated by Django 4.1.3 on 2023-01-05 11:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_remove_article_filename_labeledsentence_filename'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='news_link',
            field=models.TextField(primary_key=True, serialize=False, unique=True),
        ),
        migrations.AlterField(
            model_name='labeledsentence',
            name='sentence',
            field=models.TextField(primary_key=True, serialize=False, unique=True),
        ),
    ]