"""
Management command to create and manage API tokens for authentication.

Usage:
    # Create token for a user
    python manage.py create_api_token -u john
    
    # List all tokens
    python manage.py create_api_token --list
    
    # Create service tokens
    python manage.py create_api_token --service payment-service
    python manage.py create_api_token --service shipping-service
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from store.auth import create_service_token


class Command(BaseCommand):
    help = 'Create and manage API tokens for authentication'

    def add_arguments(self, parser):
        parser.add_argument(
            '-u', '--user',
            type=str,
            help='Username to create token for'
        )
        parser.add_argument(
            '--service',
            type=str,
            help='Create token for a microservice'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all existing tokens'
        )
        parser.add_argument(
            '--delete',
            type=str,
            help='Delete token for user'
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_tokens()
        elif options['delete']:
            self.delete_token(options['delete'])
        elif options['user']:
            self.create_user_token(options['user'])
        elif options['service']:
            self.create_service_token_cmd(options['service'])
        else:
            self.stdout.write(self.style.WARNING('No action specified. Use --help for usage.'))

    def create_user_token(self, username):
        """Create token for a regular user."""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')

        token, created = Token.objects.get_or_create(user=user)

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Token created for user "{username}"')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠ Token already exists for user "{username}"')
            )

        self.stdout.write(f'\nToken: {token.key}')
        self.stdout.write(f'\nUsage:')
        self.stdout.write(f'  curl -H "Authorization: Bearer {token.key}" \\')
        self.stdout.write(f'       http://localhost:8000/api/books/')

    def create_service_token_cmd(self, service_name):
        """Create token for a microservice."""
        try:
            token = create_service_token(service_name)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Token created for service "{service_name}"')
            )
            self.stdout.write(f'\nToken: {token}')
            self.stdout.write(f'\nUsage in service:')
            self.stdout.write(f'  Authorization: Bearer {token}')
            self.stdout.write(f'\nEnvironment variable:')
            self.stdout.write(f'  export PAYMENT_SERVICE_TOKEN={token}')
        except Exception as e:
            raise CommandError(f'Failed to create service token: {str(e)}')

    def list_tokens(self):
        """List all existing tokens."""
        tokens = Token.objects.select_related('user').all()

        if not tokens.exists():
            self.stdout.write(self.style.WARNING('No tokens found'))
            return

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('API TOKENS')
        self.stdout.write('=' * 70)

        for token in tokens:
            user_type = 'Service' if token.user.username.startswith('service_') else 'User'
            self.stdout.write(
                f'\n{user_type}: {token.user.username}\n'
                f'  Token: {token.key}\n'
                f'  Created: {token.user.date_joined}\n'
                f'  Active: {"Yes" if token.user.is_active else "No"}'
            )

        self.stdout.write('\n' + '=' * 70)

    def delete_token(self, username):
        """Delete token for a user."""
        try:
            user = User.objects.get(username=username)
            Token.objects.filter(user=user).delete()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Token deleted for user "{username}"')
            )
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')
