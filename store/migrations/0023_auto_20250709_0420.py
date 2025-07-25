# Generated by Django 5.2 on 2025-07-09 11:20

from django.db import migrations

def create_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    if not User.objects.filter(username='mfy25').exists():
        User.objects.create_superuser(
            username='mfy25',
            email='',
            password='Admin@23',
        )

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0022_alter_wishlist_unique_together_alter_review_user_and_more'),
    ]

    operations = [
        migrations.RunPython(create_superuser),
    ]
