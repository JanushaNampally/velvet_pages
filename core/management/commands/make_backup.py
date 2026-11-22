from django.core.management.base import BaseCommand

from accounts.models import Owner
from core.backup import create_backup, prune_backups


class Command(BaseCommand):
    help = "Create a verified backup archive (schedule with cron). Needs no passphrase: data stays encrypted."

    def add_arguments(self, parser):
        parser.add_argument("--keep", type=int, default=10)

    def handle(self, *args, **opts):
        owner = Owner.objects.first()
        if not owner:
            self.stderr.write("No owner yet.")
            return
        b = create_backup(owner, "scheduled")
        prune_backups(opts["keep"])
        self.stdout.write(f"{b.status}: {b.storage_key} ({b.note})")
