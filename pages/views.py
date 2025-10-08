from django.shortcuts import render

def refund(request):
    return render(request, 'pages/refund.html')

def shipping(request):
    return render(request, 'pages/shipping.html')

def privacy(request):
    return render(request, 'pages/privacy.html')

def terms(request):
    return render(request, 'pages/terms.html')
