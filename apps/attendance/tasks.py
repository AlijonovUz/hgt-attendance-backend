from celery import shared_task
from django.utils import timezone

from apps.users.models import User, WeekDay, Holiday
from apps.attendance.models import Attendance
from apps.notifications.models import Notification


@shared_task
def check_late_attendances_task():
    now = timezone.localtime()
    today = now.date()
    current_time = now.time()

    if Holiday.objects.filter(start_date__lte=today, end_date__gte=today).exists():
        return "Bugun dam olish kuni - xodimlar tekshirilmaydi"

    current_weekday = today.weekday()
    try:
        weekday_obj = WeekDay.objects.get(day_number=current_weekday)
    except WeekDay.DoesNotExist:
        return "WeekDay topilmadi"

    users = User.objects.filter(
        is_active=True,
        is_fired=False,
        schedule__isnull=False,
        schedule__mandatory_days=weekday_obj
    ).select_related('schedule')

    if not users.exists():
        return "Tekshirish uchun xodimlar yo'q"

    today_attendances = Attendance.objects.filter(
        created_at__date=today, user__in=users
    ).values("user_id", "event_type")

    today_notifications = Notification.objects.filter(
        created_at__date=today, user__in=users, extra_data__has_key="type"
    ).values("user_id", "extra_data")

    user_attendance_map = {}
    for att in today_attendances:
        uid = att["user_id"]
        if uid not in user_attendance_map:
            user_attendance_map[uid] = set()
        user_attendance_map[uid].add(att["event_type"])

    user_notification_map = {}
    for notf in today_notifications:
        uid = notf["user_id"]
        if uid not in user_notification_map:
            user_notification_map[uid] = set()
        extra_type = notf["extra_data"].get("type")
        if extra_type:
            user_notification_map[uid].add(extra_type)

    late_work_count = 0
    late_lunch_count = 0

    notifications_to_create = []

    for user in users:
        schedule = user.schedule
        uid = user.id
        atts = user_attendance_map.get(uid, set())
        notfs = user_notification_map.get(uid, set())

        if schedule.work_start_time and current_time > schedule.work_start_time:
            if Attendance.EventType.CHECK_IN not in atts:
                if "late_for_work" not in notfs:
                    notifications_to_create.append(
                        Notification(
                            user_id=uid,
                            title_uz_latn="Kechikish",
                            title_uz_cyrl="Кечикиш",
                            title_ru="Опоздание",
                            message_uz_latn=f"Hurmatli {user.full_name}. Siz ish boshlash vaqtidan kech qolmoqdasiz!",
                            message_uz_cyrl=f"Ҳурматли {user.full_name}. Сиз иш бошлаш вақтидан кеч қолмоқдасиз!",
                            message_ru=f"Уважаемый(ая) {user.full_name}. Вы опаздываете на работу!",
                            extra_data={"type": "late_for_work"},
                        )
                    )
                    late_work_count += 1

        if schedule.lunch_end_time and current_time > schedule.lunch_end_time:
            if Attendance.EventType.LUNCH_START in atts:
                if (
                    Attendance.EventType.LUNCH_END not in atts
                    and Attendance.EventType.CHECK_OUT not in atts
                ):
                    if "late_for_lunch" not in notfs:
                        notifications_to_create.append(
                            Notification(
                                user_id=uid,
                                title_uz_latn="Tushlikdan kechikish",
                                title_uz_cyrl="Тушликдан кечикиш",
                                title_ru="Опоздание с обеда",
                                message_uz_latn=f"Hurmatli {user.full_name}. Siz tushlikdan qaytish vaqtidan kech qolmoqdasiz!",
                                message_uz_cyrl=f"Ҳурматли {user.full_name}. Сиз тушликдан қайтиш вақтидан кеч қолмоқдасиз!",
                                message_ru=f"Уважаемый(ая) {user.full_name}. Вы опаздываете с обеда!",
                                extra_data={"type": "late_for_lunch"},
                            )
                        )
                        late_lunch_count += 1

    if notifications_to_create:
        Notification.objects.bulk_create(notifications_to_create, batch_size=1000)

        from apps.notifications.tasks import mass_notification_sender
        import uuid
        
        now_iso = timezone.now().isoformat()
        message_data_list = []
        
        for notif in notifications_to_create:
            message_data_list.append({
                "user_id": str(notif.user_id),
                "id": str(notif.id) if notif.id else str(uuid.uuid4()),
                "title_uz_latn": notif.title_uz_latn,
                "title_uz_cyrl": notif.title_uz_cyrl,
                "title_ru": notif.title_ru,
                "message_uz_latn": notif.message_uz_latn,
                "message_uz_cyrl": notif.message_uz_cyrl,
                "message_ru": notif.message_ru,
                "extra_data": notif.extra_data,
                "created_at": now_iso,
            })

        batch_size = 500
        for i in range(0, len(message_data_list), batch_size):
            batch = message_data_list[i : i + batch_size]
            mass_notification_sender.delay(batch)

    return f"Ishga kechikkanlar: {late_work_count}, Tushlikdan kechikkanlar: {late_lunch_count}"
