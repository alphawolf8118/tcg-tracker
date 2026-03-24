import requests
import time
from django.core.management.base import BaseCommand
from games.models import MTGSet, MTGCard, Pokemon

class Command(BaseCommand):
    help = 'Fetch only physical MTG sets/cards from Scryfall and Pokémon from PokeAPI'

    def handle(self, *args, **kwargs):
        # MTG Sets and Cards
        sets_url = 'https://api.scryfall.com/sets'
        response = requests.get(sets_url)
        if response.status_code == 200:
            sets_data = response.json()['data']
            self.stdout.write(f"Found {len(sets_data)} sets")
            physical_sets_count = 0
            for i, s in enumerate(sets_data, 1):
                self.stdout.write(f"Processing set {i}/{len(sets_data)}: {s['name']} ({s['code']})")
                # Skip digital sets unless explicitly allowed (e.g., spm, spe, mar)
                if s.get('digital', False) and s['code'] not in ['spm', 'spe', 'mar']:
                    self.stdout.write(self.style.WARNING(f"  Skipping digital set: {s['name']} ({s['code']})"))
                    continue
                # Skip sets with 4-letter codes
                if len(s['code']) >= 4:
                    self.stdout.write(self.style.WARNING(f"  Skipping 4-letter code set: {s['name']} ({s['code']})"))
                    continue
                physical_sets_count += 1
                mtg_set, _ = MTGSet.objects.update_or_create(
                    code=s['code'],
                    defaults={
                        'name': s['name'],
                        'release_date': s['released_at'],
                        'card_count': s['card_count'],
                        'digital': s.get('digital', False),
                        'symbol_url': s.get('icon_svg_uri', '') or s.get('symbol', '')  # Add symbol URL
                    }
                )
                self.stdout.write(f"  Updated {mtg_set.name} with symbol URL: {mtg_set.symbol_url}")
                cards_url = s['search_uri']  # Use the set's official search URI for full pagination
                cards_fetched = 0
                while cards_url:
                    cards_response = requests.get(cards_url)
                    if cards_response.status_code == 200:
                        cards_data = cards_response.json()
                        for c in cards_data['data']:
                            MTGCard.objects.update_or_create(
                                set=mtg_set,
                                collector_number=c['collector_number'],
                                defaults={
                                    'name': c['name'],
                                    'image_url': c.get('image_uris', {}).get('normal', ''),
                                }
                            )
                            cards_fetched += 1
                        self.stdout.write(f"  Fetched {len(cards_data['data'])} cards (total for set: {cards_fetched})")
                        cards_url = cards_data.get('next_page')
                    else:
                        self.stdout.write(self.style.ERROR(f"  Error fetching cards: {cards_response.status_code}"))
                        break
                    time.sleep(0.2)  # Respect rate limit
                self.stdout.write(f"  Total cards for set: {cards_fetched}/{mtg_set.card_count}")
            self.stdout.write(self.style.SUCCESS(f'MTG data fetched successfully! Processed {physical_sets_count} physical sets.'))
        else:
            self.stdout.write(self.style.ERROR(f'Error fetching sets: {response.status_code}'))

        # Pokémon (dynamic fetch, limited to 1025)
        self.stdout.write("Fetching Pokémon data...")
        base_url = 'https://pokeapi.co/api/v2/pokemon'
        pokemon_count = 0
        url = base_url
        while url and pokemon_count < 1025:  # Stop at 1025
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for poke in data['results']:
                        if pokemon_count >= 1025:
                            break
                        poke_response = requests.get(poke['url'], timeout=10)
                        if poke_response.status_code == 200:
                            poke_data = poke_response.json()
                            name = poke_data['name'].title()
                            image_url = poke_data['sprites']['other']['official-artwork']['front_default'] or ''
                            dex_number = poke_data['id']
                            if dex_number <= 1025:  # Ensure dex_number <= 1025
                                Pokemon.objects.update_or_create(
                                    dex_number=dex_number,
                                    defaults={'name': name, 'image_url': image_url}
                                )
                                pokemon_count += 1
                                self.stdout.write(self.style.SUCCESS(f"Processed Pokémon #{dex_number}: {name}"))
                    url = data.get('next')
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to fetch Pokémon list: {response.status_code}"))
                    break
                time.sleep(0.2)
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Network error fetching Pokémon: {e}"))
                break
        self.stdout.write(self.style.SUCCESS(f"Total Pokémon saved: {pokemon_count}"))