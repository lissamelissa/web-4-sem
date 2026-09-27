from django.core.management.base import BaseCommand
from django.db.models import Count

from plapp.models import user


class Command(BaseCommand):
    help = "Удаляет дубли username, оставляя запись с наименьшим id (нужно перед unique=True)."

    def handle(self, *args, **options):
        dupes = list(
            user.objects.values('username')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )

        if not dupes:
            self.stdout.write(self.style.SUCCESS("Дублей username не найдено."))
            return

        for d in dupes:
            qs = user.objects.filter(username=d['username']).order_by('id')
            keep = qs.first()
            removed = 0
            for extra in qs.exclude(pk=keep.pk):
                self.stdout.write(f"Удаляю дубль: id={extra.pk}, username={extra.username}")
                extra.delete()
                removed += 1
            self.stdout.write(self.style.SUCCESS(
                f"username={d['username']!r}: оставлен id={keep.pk}, удалено дублей: {removed}"
            ))

        self.stdout.write(self.style.SUCCESS("Готово."))
