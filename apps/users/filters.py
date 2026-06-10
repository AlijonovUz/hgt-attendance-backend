import django_filters

from .models import Department, Position, User


class UserFilter(django_filters.FilterSet):
    class Meta:
        model = User
        fields = [
            "is_active",
            "is_fired",
            "branch",
            "department",
            "position",
            "role",
        ]


class DepartmentFilter(django_filters.FilterSet):
    class Meta:
        model = Department
        fields = ["branch"]


class PositionFilter(django_filters.FilterSet):
    class Meta:
        model = Position
        fields = ["department", "department__branch"]
