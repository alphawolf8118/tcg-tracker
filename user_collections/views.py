from django.db.models import Exists, OuterRef, IntegerField, Func, Value , CharField # Removed Cast from here
from django.db.models.functions import Cast  # Added correct import for Cast
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django.http import HttpResponse
import csv
from io import StringIO
from games.models import MTGSet, MTGCard, Pokemon
from .models import UserMTGCollection, UserPokemonCollection, Binder, BinderSet
from urllib.parse import urlencode
from collections import OrderedDict
import datetime
import logging
import time

logger = logging.getLogger(__name__)

@login_required
def pokemon_pokedex(request):
    query = request.GET.get('q', '')
    pokemon_list = Pokemon.objects.all()
    total_pokemon = pokemon_list.count()
    collected_count = UserPokemonCollection.objects.filter(user=request.user, collected=True).count()
    progress = (collected_count / total_pokemon * 100) if total_pokemon > 0 else 0
    
    if query:
        pokemon_list = pokemon_list.filter(models.Q(name__icontains=query) | models.Q(dex_number__icontains=query))
    paginator = Paginator(pokemon_list, 100)
    page_number = request.GET.get('page', '1')
    page_obj = paginator.get_page(page_number)
    
    # Attach collected status to each Pokemon object
    collections = UserPokemonCollection.objects.filter(user=request.user)
    collection_dict = {c.pokemon.id: c.collected for c in collections}
    for pokemon in page_obj:
        pokemon.collected = collection_dict.get(pokemon.id, False)
    
    if request.method == 'POST':
        pokemon_id = request.POST.get('pokemon_id')
        page = request.POST.get('page', page_number)
        query = request.POST.get('query', query)
        collected = 'collected' in request.POST
        logger.debug(f"POST: pokemon_id={pokemon_id}, page={page}, query={query}, collected={collected}")
        try:
            pokemon = Pokemon.objects.get(id=pokemon_id)
            coll, created = UserPokemonCollection.objects.get_or_create(user=request.user, pokemon=pokemon)
            coll.collected = collected
            coll.save()
            logger.debug(f"Saved: pokemon_id={pokemon_id}, collected={coll.collected}, created={created}")
            # Construct redirect URL
            params = {'page': page}
            if query:
                params['q'] = query
            redirect_url = f"/collections/pokemon/?{urlencode(params)}#pokemon-{pokemon_id}"
            logger.debug(f"Redirecting to: {redirect_url}")
            return redirect(redirect_url)
        except Exception as e:
            logger.error(f"Error saving collection: {e}")
            return redirect('user_collections:pokemon_pokedex')
    
    return render(request, 'user_collections/pokemon_pokedex.html', {
        'pokemon_list': page_obj,
        'query': query,
        'total_pokemon': total_pokemon,
        'collected_count': collected_count,
        'progress': progress
    })

@login_required
def mtg_collections(request):
    binders = Binder.objects.filter(user=request.user)
    binder_sets = BinderSet.objects.filter(binder__user=request.user).select_related('binder', 'mtg_set')
    
    # Group sets by binder
    binder_dict = {binder.id: {'binder': binder, 'sets': []} for binder in binders}
    binder_dict[None] = {'binder': None, 'sets': []}  # For unassigned sets
    all_set_ids = set(MTGSet.objects.values_list('id', flat=True))
    assigned_set_ids = set()
    
    for bs in binder_sets:
        set_info = bs.mtg_set
        total_cards = set_info.card_count
        collected_count = UserMTGCollection.objects.filter(
            user=request.user,
            card__set=set_info
        ).filter(models.Q(collected=True) | models.Q(is_foil=True)).count()
        set_info.progress = (collected_count / total_cards * 100) if total_cards > 0 else 0
        set_info.collected_count = collected_count
        binder_dict[bs.binder.id]['sets'].append(set_info)
        assigned_set_ids.add(set_info.id)
    
    # Add unassigned sets to 'None' binder
    unassigned_sets = MTGSet.objects.filter(id__in=(all_set_ids - assigned_set_ids))
    for s in unassigned_sets:
        total_cards = s.card_count
        collected_count = UserMTGCollection.objects.filter(
            user=request.user,
            card__set=s
        ).filter(models.Q(collected=True) | models.Q(is_foil=True)).count()
        s.progress = (collected_count / total_cards * 100) if total_cards > 0 else 0
        s.collected_count = collected_count
        binder_dict[None]['sets'].append(s)
    
    # Create a list of items (binders or individual sets) sorted by release date
    items = []
    for binder_id, data in binder_dict.items():
        if data['binder']:  # Binder with sets
            if data['sets']:
                # Sort sets within binder by release date
                data['sets'].sort(key=lambda x: x.release_date or datetime.date.max, reverse=True)
                # Use the most recent set's release date for the binder
                most_recent_date = min([s.release_date or datetime.date.max for s in data['sets']])
                items.append({'type': 'binder', 'binder': data['binder'], 'sets': data['sets'], 'sort_date': most_recent_date})
        else:  # Unassigned sets
            for s in data['sets']:
                items.append({'type': 'set', 'set': s, 'sort_date': s.release_date or datetime.date.max})
    
    # Sort items by sort_date (newest first)
    items.sort(key=lambda x: x['sort_date'], reverse=True)
    
    # Pagination
    paginator = Paginator(items, 50)  # 50 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_binder':
            binder_name = request.POST.get('binder_name')
            if binder_name:
                try:
                    Binder.objects.create(user=request.user, name=binder_name)
                    logger.debug(f"Created binder: {binder_name}")
                    return redirect('user_collections:mtg_collections')
                except Exception as e:
                    logger.error(f"Error creating binder: {e}")
                    return render(request, 'user_collections/mtg_collections.html', {
                        'items': page_obj,
                        'binders': binders,
                        'error': 'Failed to create binder. Please try again.'
                    })
        elif action == 'add_set_to_binder':
            binder_id = request.POST.get('binder_id')
            set_id = request.POST.get('set_id')
            try:
                binder = Binder.objects.get(id=binder_id, user=request.user)
                mtg_set = MTGSet.objects.get(id=set_id)
                BinderSet.objects.get_or_create(binder=binder, mtg_set=mtg_set)
                logger.debug(f"Added set {mtg_set.name} to binder {binder.name}")
                return redirect('user_collections:mtg_collections')
            except Exception as e:
                logger.error(f"Error adding set to binder: {e}")
                return render(request, 'user_collections/mtg_collections.html', {
                    'items': page_obj,
                    'binders': binders,
                    'error': 'Failed to add set to binder. Please try again.'
                })
    
    return render(request, 'user_collections/mtg_collections.html', {
        'items': page_obj,
        'binders': binders,
        'error': None
    })

@login_required
def mtg_set_detail(request, set_id):
    mtg_set = get_object_or_404(MTGSet, id=set_id)
    # Get all cards for the set
    all_cards = MTGCard.objects.filter(set=mtg_set)
    # Get user's collection for this set
    user_collection = UserMTGCollection.objects.filter(user=request.user, card__set=mtg_set)
    collected_cards = user_collection.values_list('card_id', flat=True)

    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        page = request.POST.get('page', '1')
        if card_id:
            card = get_object_or_404(MTGCard, id=card_id)
            # Get or create the user's collection entry for this card
            collection_entry, created = UserMTGCollection.objects.get_or_create(
                user=request.user,
                card=card,
                defaults={'collected': False, 'is_foil': False}
            )
            # Update based on checkbox states
            collected = 'collected' in request.POST and request.POST['collected'] == 'on'
            is_foil = 'foil' in request.POST and request.POST['foil'] == 'on'
            if collection_entry.collected != collected or collection_entry.is_foil != is_foil:
                collection_entry.collected = collected
                collection_entry.is_foil = is_foil
                collection_entry.save()
                logger.debug(f"Updated collection for card {card.name} by user {request.user.username}")
        # Redirect to the same page with the current page number
        return redirect(f'/collections/mtg/set/{set_id}/?page={page}')

    # For GET request (display)
    # For SQLite, try casting and fallback to string sort
    try:
        cards = all_cards.annotate(
            collected=Exists(user_collection.filter(card=OuterRef('pk'), collected=True)),
            is_foil=Exists(user_collection.filter(card=OuterRef('pk'), is_foil=True)),
            sort_number=Cast('collector_number', IntegerField())
        ).order_by('sort_number')
    except (ValueError, FieldError):
        cards = all_cards.annotate(
            collected=Exists(user_collection.filter(card=OuterRef('pk'), collected=True)),
            is_foil=Exists(user_collection.filter(card=OuterRef('pk'), is_foil=True))
        ).order_by('collector_number')

    # Pagination
    paginator = Paginator(cards, 12)  # 12 cards per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'set': mtg_set,
        'cards': page_obj,
        'total_cards': all_cards.count(),
        'collected_count': user_collection.filter(collected=True).count() + user_collection.filter(is_foil=True).count(),
        'progress': min((user_collection.filter(collected=True).count() + user_collection.filter(is_foil=True).count()) / all_cards.count() * 100, 100)
    }
    return render(request, 'user_collections/mtg_set_detail.html', context)

@login_required
def create_binder(request):
    if request.method == 'POST':
        binder_name = request.POST.get('binder_name')
        if binder_name:
            try:
                Binder.objects.create(user=request.user, name=binder_name)
                logger.debug(f"Created binder: {binder_name}")
                return redirect('user_collections:mtg_collections')
            except Exception as e:
                logger.error(f"Error creating binder: {e}")
                return redirect('user_collections:mtg_collections')
    return redirect('user_collections:mtg_collections')

@login_required
def binder_detail(request, binder_id):
    try:
        binder = Binder.objects.get(id=binder_id, user=request.user)
        sets = MTGSet.objects.filter(binderset__binder=binder).order_by('-release_date')
        for s in sets:
            total_cards = s.card_count
            collected_count = UserMTGCollection.objects.filter(
                user=request.user, 
                card__set=s
            ).filter(models.Q(collected=True) | models.Q(is_foil=True)).count()
            s.progress = (collected_count / total_cards * 100) if total_cards > 0 else 0
            s.collected_count = collected_count
        return render(request, 'user_collections/binder_detail.html', {
            'binder': binder,
            'sets': sets
        })
    except Binder.DoesNotExist:
        logger.error(f"Binder {binder_id} not found for user {request.user.username}")
        return redirect('user_collections:mtg_collections')

@login_required
def delete_binder(request, binder_id):
    try:
        binder = Binder.objects.get(id=binder_id, user=request.user)
        binder_name = binder.name
        binder.delete()
        logger.debug(f"Deleted binder: {binder_name} for user {request.user.username}")
        return redirect('user_collections:mtg_collections')
    except Binder.DoesNotExist:
        logger.error(f"Binder {binder_id} not found for user {request.user.username}")
        return redirect('user_collections:mtg_collections')
    
from django.http import HttpResponse
import csv
from io import StringIO

@login_required
def export_missing_pokemon(request):
    # Get all Pokémon
    all_pokemon = Pokemon.objects.all()
    total_pokemon = all_pokemon.count()
    
    # Get collected Pokémon for the user
    collected_ids = UserPokemonCollection.objects.filter(user=request.user, collected=True).values_list('pokemon_id', flat=True)
    
    # Get missing Pokémon (not collected)
    missing_pokemon = all_pokemon.exclude(id__in=collected_ids)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="missing_pokemon_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Dex Number', 'Name', 'Image URL', 'Collected'])
    
    for pokemon in missing_pokemon:
        writer.writerow([pokemon.dex_number, pokemon.name, pokemon.image_url, 'No'])
    
    logger.debug(f"Exported {missing_pokemon.count()} missing Pokémon for user {request.user.username}")
    return response

@login_required
def export_missing_mtg(request):
    if request.method == 'POST' and 'selected_sets' in request.POST:
        selected_set_ids = request.POST.getlist('selected_sets')
        sets_to_export = MTGSet.objects.filter(id__in=selected_set_ids)
    else:
        # Default to all sets with missing cards
        all_sets = MTGSet.objects.all()
        missing_sets = []
        for set in all_sets:
            collected_in_set = UserMTGCollection.objects.filter(
                user=request.user,
                card__set=set
            ).aggregate(
                collected_count=models.Count('id', filter=models.Q(collected=True) | models.Q(is_foil=True))
            )['collected_count'] or 0
            total_cards = set.card_count
            if collected_in_set < total_cards:
                missing_sets.append(set)
        sets_to_export = missing_sets

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="missing_mtg_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Set Code', 'Set Name', 'Release Date', 'Total Cards', 'Collected Cards', 'Missing Cards'])

    for set in sets_to_export:
        collected = UserMTGCollection.objects.filter(
            user=request.user,
            card__set=set
        ).aggregate(
            collected_count=models.Count('id', filter=models.Q(collected=True) | models.Q(is_foil=True))
        )['collected_count'] or 0
        missing = set.card_count - collected
        writer.writerow([set.code, set.name, set.release_date, set.card_count, collected, missing])

    logger.debug(f"Exported {len(sets_to_export)} MTG sets for user {request.user.username}")
    return response

@login_required
def export_missing_cards(request, set_id):
    if request.method == 'GET':
        mtg_set = get_object_or_404(MTGSet, id=set_id)
        # Get all cards in the set
        all_cards = MTGCard.objects.filter(set=mtg_set)
        # Get collected card IDs for the user
        # Combine Q object with other filters using &
        query = Q(user=request.user) & Q(card__set=mtg_set) & (Q(collected=True) | Q(is_foil=True))
        collected_card_ids = UserMTGCollection.objects.filter(query).values_list('card__id', flat=True)
        missing_cards = all_cards.exclude(id__in=collected_card_ids)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="missing_cards_{mtg_set.code}_{timezone.now().strftime('%Y%m%d')}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Card Name', 'Collector Number', 'Rarity', 'Missing'])

        for card in missing_cards:
            writer.writerow([card.name, card.collector_number, getattr(card, 'rarity', 'N/A'), 'Yes'])

        logger.debug(f"Exported {missing_cards.count()} missing cards from set {mtg_set.name} for user {request.user.username}")
        return response
    else:
        return redirect('user_collections:mtg_set_detail', set_id=set_id)
    
@login_required
def delete_set(request, set_id):
    try:
        with transaction.atomic():  # Ensure atomic deletion
            mtg_set = MTGSet.objects.get(id=set_id)
            set_name = mtg_set.name
            # Delete all BinderSet records referencing this set
            BinderSet.objects.filter(mtg_set=mtg_set).delete()
            mtg_set.delete()
            logger.debug(f"Deleted set: {set_name} (ID {set_id}) for user {request.user.username}")
        return redirect('user_collections:mtg_collections')
    except MTGSet.DoesNotExist:
        logger.error(f"Set {set_id} not found")
        return redirect('user_collections:mtg_collections')
    except Exception as e:
        logger.error(f"Error deleting set {set_id}: {str(e)}")
        return redirect('user_collections:mtg_collections')