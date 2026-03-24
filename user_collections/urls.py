from django.urls import path
from . import views

app_name = 'user_collections'

urlpatterns = [
    path('pokemon/', views.pokemon_pokedex, name='pokemon_pokedex'),
    path('mtg/', views.mtg_collections, name='mtg_collections'),
    path('mtg/set/<int:set_id>/', views.mtg_set_detail, name='mtg_set_detail'),
    path('mtg/binder/create/', views.create_binder, name='create_binder'),
    path('mtg/binder/<int:binder_id>/', views.binder_detail, name='binder_detail'),
    path('delete_binder/<int:binder_id>/', views.delete_binder, name='delete_binder'),
    path('export_missing_pokemon/', views.export_missing_pokemon, name='export_missing_pokemon'),
    path('export_missing_mtg/', views.export_missing_mtg, name='export_missing_mtg'),
    path('delete_set/<int:set_id>/', views.delete_set, name='delete_set'),
    path('export_missing_cards/<int:set_id>/', views.export_missing_cards, name='export_missing_cards'),
]