# Generated by Django 4.1.1 on 2023-01-25 23:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rsr', '0002_store_merchandiser'),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='name',
            field=models.CharField(choices=[('Safeway', 'Safeway'), ('Target', 'Target'), ('Lucky', 'Lucky'), ('FoodMaxx', 'FoodMaxx'), ('SaveMart', 'SaveMart'), ('Lunardis', 'Lunardis'), ('Nob Hill', 'Nob Hill'), ('Wholefoods', 'Wholefoods'), ('BerkeleyBowl', 'BerkeleyBowl'), ('Pak n Save', 'Pak n Save'), ('Village Market', 'Village Market')], default='Safeway', max_length=25),
        ),
    ]
