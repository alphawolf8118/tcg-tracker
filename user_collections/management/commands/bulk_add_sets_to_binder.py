from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user_collections.models import Binder, BinderSet
from games.models import MTGSet

class Command(BaseCommand):
    help = 'Bulk add multiple sets to a binder for a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user')
        parser.add_argument('binder_name', type=str, help='Name of the binder')
        parser.add_argument('set_codes', nargs='+', type=str, help='Set codes to add (space-separated, e.g., SPM SPE MAR)')

    def handle(self, *args, **options):
        username = options['username']
        binder_name = options['binder_name']
        set_codes = options['set_codes']

        try:
            user = User.objects.get(username=username)
            binder = Binder.objects.get(user=user, name=binder_name)
            for set_code in set_codes:
                try:
                    mtg_set = MTGSet.objects.get(code__iexact=set_code)
                    BinderSet.objects.get_or_create(binder=binder, mtg_set=mtg_set)
                    self.stdout.write(self.style.SUCCESS(f'Added set {set_code} to binder {binder_name} for user {username}'))
                except MTGSet.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Set with code {set_code} not found'))
            self.stdout.write(self.style.SUCCESS('Bulk add completed'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
        except Binder.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Binder {binder_name} not found for user {username}'))