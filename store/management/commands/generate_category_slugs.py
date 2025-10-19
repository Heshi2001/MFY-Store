from django.core.management.base import BaseCommand
from django.utils.text import slugify
from store.models import Category

class Command(BaseCommand):
    help = "Generate slugs for categories that don't have one."

    def handle(self, *args, **options):
        updated = 0
        for category in Category.objects.all():
            if not category.slug:
                base_slug = slugify(category.name)
                slug = base_slug
                counter = 1
                # ensure uniqueness
                while Category.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                category.slug = slug
                category.save()
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"Generated slug for: {category.name} -> {slug}"))

        if updated == 0:
            self.stdout.write(self.style.WARNING("All categories already have slugs."))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Done! Generated {updated} slugs."))
