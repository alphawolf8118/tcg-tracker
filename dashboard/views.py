from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    tcg_list = [
        {"name": "Magic: The Gathering", "url": "/collections/mtg/"},
        {"name": "Pokémon", "url": "/collections/pokemon/"},
    ]
    return render(request, 'dashboard/dashboard.html', {'tcg_list': tcg_list})