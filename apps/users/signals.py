from django.db.models.signals import post_migrate
from django.dispatch import receiver
from apps.users.models import Permission, Role


@receiver(post_migrate)
def auto_create_permissions_and_roles(sender, **kwargs):
    if sender.name != "apps.users":
        return

    PERMISSIONS_LIST = [
        ("employee_add", "Xodim qo'shish"),
        ("employee_edit", "Xodim tahrirlash"),
        ("employee_fire", "Xodimni ishdan bo'shatish"),
        ("employee_block", "Xodimni bloklash"),
        ("employee_view_profile", "Xodim profilini ko'rish"),
        ("attendance_check_in", "Ishga kelishni qayd qilish"),
        ("attendance_lunch_out", "Tushlikka chiqish"),
        ("attendance_lunch_in", "Tushlikdan qaytish"),
        ("attendance_check_out", "Ishdan ketish"),
        ("attendance_view_history_self", "O'zining davomat tarixini ko'rish"),
        ("attendance_view_history_dept", "Bo'limining davomat tarixini ko'rish"),
        ("attendance_view_history_all", "Barcha davomat tarixini ko'rish"),
        ("geozone_create", "Geozona yaratish"),
        ("geozone_edit", "Geozona tahrirlash"),
        ("geozone_delete", "Geozona o'chirish"),
        ("geozone_view", "Geozonalarni ko'rish"),
        ("gps_view_history", "Marshrut tarixini ko'rish"),
        ("kpi_view_self", "O'zining KPI ni ko'rish"),
        ("kpi_view_dept", "Bo'lim KPI ni ko'rish"),
        ("kpi_view_all", "Barcha KPI ni ko'rish"),
        ("report_view_daily", "Kunlik hisobot ko'rish"),
        ("report_view_weekly", "Haftalik hisobot ko'rish"),
        ("report_view_monthly", "Oylik hisobot ko'rish"),
        ("report_export_excel", "Excel eksport qilish"),
        ("report_export_pdf", "PDF eksport qilish"),
        ("branch_manage", "Filiallarni boshqarish"),
        ("department_manage", "Bo'limlarni boshqarish"),
        ("position_manage", "Lavozimlarni boshqarish"),
        ("role_manage", "Rollar va huquqlarni boshqarish"),
        ("audit_log_view", "Audit loglarni ko'rish"),
    ]

    for code, name in PERMISSIONS_LIST:
        Permission.objects.get_or_create(code=code, defaults={"name": name})

    ROLES_DATA = {
        "Xodim": [
            "attendance_check_in",
            "attendance_lunch_out",
            "attendance_lunch_in",
            "attendance_check_out",
            "attendance_view_history_self",
            "employee_view_profile",
            "kpi_view_self",
        ],
        "Bo'lim boshlig'i": [
            "attendance_check_in",
            "attendance_lunch_out",
            "attendance_lunch_in",
            "attendance_check_out",
            "attendance_view_history_dept",
            "employee_view_profile",
            "kpi_view_dept",
            "report_view_daily",
        ],
        "Kadrlar": [
            "attendance_check_in",
            "attendance_lunch_out",
            "attendance_lunch_in",
            "attendance_check_out",
            "attendance_view_history_all",
            "employee_view_profile",
            "kpi_view_all",
            "employee_add",
            "employee_edit",
            "employee_fire",
            "employee_block",
            "report_view_daily",
            "report_view_weekly",
            "report_view_monthly",
            "report_export_excel",
            "report_export_pdf",
        ],
        "Markaziy apparat": [
            "attendance_check_in",
            "attendance_lunch_out",
            "attendance_lunch_in",
            "attendance_check_out",
            "attendance_view_history_all",
            "employee_view_profile",
            "kpi_view_all",
            "report_view_daily",
            "report_view_weekly",
            "report_view_monthly",
            "report_export_excel",
            "report_export_pdf",
            "geozone_view",
        ],
        "Admin": [
            "attendance_check_in",
            "attendance_lunch_out",
            "attendance_lunch_in",
            "attendance_check_out",
            "attendance_view_history_all",
            "employee_view_profile",
            "kpi_view_all",
            "employee_add",
            "employee_edit",
            "employee_fire",
            "employee_block",
            "report_view_daily",
            "report_view_weekly",
            "report_view_monthly",
            "report_export_excel",
            "report_export_pdf",
            "geozone_create",
            "geozone_edit",
            "geozone_delete",
            "geozone_view",
            "gps_view_history",
            "branch_manage",
            "department_manage",
            "position_manage",
            "role_manage",
            "audit_log_view",
        ],
    }

    for role_name, perms in ROLES_DATA.items():
        role, created = Role.objects.get_or_create(name=role_name)
        perm_objs = Permission.objects.filter(code__in=perms)
        role.permissions.add(*perm_objs)
