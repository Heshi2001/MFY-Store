from django.contrib import admin
from .models import SitePage

# Register your models here.
@admin.register(SitePage)
class SitePageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at')
    prepopulated_fields = {"slug": ("title",)}