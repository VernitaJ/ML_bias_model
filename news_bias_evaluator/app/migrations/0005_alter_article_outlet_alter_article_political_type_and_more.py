# Generated by Django 4.1.3 on 2022-12-20 13:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_alter_article_outlet_alter_article_topic'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='outlet',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='article',
            name='political_type',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='article',
            name='topic',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='labeledsentence',
            name='label_bias',
            field=models.CharField(max_length=50),
        ),
    ]
