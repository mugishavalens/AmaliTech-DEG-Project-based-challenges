from django.core.management.base import BaseCommand
from payments.models import IdempotencyRecord


class Command(BaseCommand):
    help = "Delete IdempotencyRecord rows older than --days (default: 7). Intended to run on a schedule (e.g. daily cron)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Delete records created more than this many days ago (default: 7).",
        )

    def handle(self, *args, **options):
        deleted_count = IdempotencyRecord.cleanup_old_records(days=options["days"])
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_count} idempotency record(s) older than {options['days']} day(s).")
        )
