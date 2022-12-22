# Generated by Django 4.1.3 on 2022-12-20 13:49

import app.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('news_link', models.CharField(max_length=200, primary_key=True, serialize=False)),
                ('article', models.TextField()),
                ('outlet', models.CharField(max_length=20)),
                ('topic', models.CharField(max_length=20)),
                ('political_type', models.CharField(max_length=10)),
                ('pub_year', models.IntegerField(null=True)),
                ('add_date', models.DateField(default=app.models.current_date)),
            ],
        ),
        migrations.CreateModel(
            name='LabeledSentence',
            fields=[
                ('sentence', models.TextField(primary_key=True, serialize=False)),
                ('label_bias', models.CharField(max_length=10)),
                ('label_opinion', models.CharField(max_length=50)),
                ('bias_words', models.TextField(blank=True)),
                ('article', models.ForeignKey(max_length=200, on_delete=django.db.models.deletion.CASCADE, to='app.article')),
            ],
        ),
    ]
