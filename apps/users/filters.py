import django_filters

from .models import Department, Position, User


class UserFilter(django_filters.FilterSet):
    region = django_filters.UUIDFilter(field_name="branch__region")
    district = django_filters.UUIDFilter(field_name="branch__district")

    class Meta:
        model = User
        fields = [
            "is_active",
            "is_fired",
            "region",
            "district",
            "branch",
            "department",
            "position",
            "role",
        ]


class DepartmentFilter(django_filters.FilterSet):
    region = django_filters.UUIDFilter(field_name="branch__region")
    district = django_filters.UUIDFilter(field_name="branch__district")

    class Meta:
        model = Department
        fields = ["branch", "region", "district"]


class PositionFilter(django_filters.FilterSet):
    region = django_filters.UUIDFilter(field_name="department__branch__region")
    district = django_filters.UUIDFilter(field_name="department__branch__district")
    branch = django_filters.UUIDFilter(field_name="department__branch")

    class Meta:
        model = Position
        fields = ["department", "branch", "region", "district"]
