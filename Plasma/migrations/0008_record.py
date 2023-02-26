# Generated by Django 4.1.3 on 2022-12-06 21:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('Plasma', '0007_ranking'),
    ]

    operations = [
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('clan', 'Clan'), ('dogtags', 'Dogtag')], max_length=255)),
                ('key', models.IntegerField(help_text='Key of the record.', verbose_name='Key')),
                ('value', models.TextField(help_text='Value of the record.', verbose_name='Value')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('persona', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Plasma.persona')),
            ],
        ),
    ]
