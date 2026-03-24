from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from user_collections.models import Binder, BinderSet, MTGSet

class Command(BaseCommand):
    help = 'Add a set to a binder for a specific user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='The username of the user')
        parser.add_argument('binder_name', type=str, help='The name of the binder')
        parser.add_argument('set_code', type=str, help='The set code (e.g., FIN)')

    def handle(self, *args, **options):
        username = options['username']
        binder_name = options['binder_name']
        set_code = options['set_code']

        try:
            user = get_user_model().objects.get(username=username)
            binder = Binder.objects.get(user=user, name=binder_name)
            mtg_set = MTGSet.objects.get(code=set_code)
            BinderSet.objects.get_or_create(binder=binder, mtg_set=mtg_set)
            self.stdout.write(self.style.SUCCESS(f'Successfully added set {set_code} to binder {binder_name} for {username}'))
        except get_user_model().DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
        except Binder.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Binder {binder_name} not found for {username}'))
        except MTGSet.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Set with code {set_code} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))