from django.shortcuts import render, get_object_or_404
from .models import SitePage

def site_page(request, slug):
    page = get_object_or_404(SitePage, slug=slug)
    return render(request, f"pages/{slug}.html", {"page": page})
