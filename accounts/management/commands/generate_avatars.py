from django.core.management.base import BaseCommand
from accounts.models import Profile


class Command(BaseCommand):
    help = 'Generate UI Avatar URLs for all existing users without avatars'

    def handle(self, *args, **kwargs):
        profiles = Profile.objects.all()
        updated = 0

        for profile in profiles:
            if not profile.avatar:
                name = (
                    profile.user.get_full_name() or
                    profile.user.username
                )
                initials = '+'.join(name.split()[:2])
                profile.avatar_url = (
                    f'https://ui-avatars.com/api/'
                    f'?name={initials}'
                    f'&size=200'
                    f'&background=60BB46'
                    f'&color=ffffff'
                    f'&bold=true'
                    f'&rounded=true'
                )
                profile.save(update_fields=['avatar_url'])
                updated += 1
                self.stdout.write(
                    f'Generated avatar for: {profile.user.username}'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone! Generated avatars for {updated} users.'
            )
        )