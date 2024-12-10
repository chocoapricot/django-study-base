from django.shortcuts import render

# Create your views here.

def list(request):
    return render(request, 'staff/simplex_list.html')

