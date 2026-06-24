from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
from apps.analytics.services.daily import DailyKPIService

class Command(BaseCommand):
    help = 'Backfills DailyAttendance records for the current month up to today.'

    def handle(self, *args, **options):
        today = timezone.localtime().date()
        start_date = today.replace(day=1)
        
        users = User.objects.filter(is_active=True, is_fired=False)
        total_users = users.count()
        
        self.stdout.write(self.style.NOTICE(f"Starting backfill from {start_date} to {today} for {total_users} users."))
        
        count = 0
        for user in users:
            current_date = start_date
            while current_date <= today:
                DailyKPIService.calculate_daily_snapshot(user, current_date)
                current_date += timedelta(days=1)
            
            count += 1
            if count % 10 == 0:
                self.stdout.write(f"Processed {count}/{total_users} users...")
                
        self.stdout.write(self.style.SUCCESS('Successfully backfilled DailyAttendance for all active users.'))
