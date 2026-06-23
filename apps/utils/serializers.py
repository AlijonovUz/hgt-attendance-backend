from rest_framework import serializers

class RegionDistrictBranchMixin(serializers.Serializer):
    region = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    branch = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    def get_region(self, obj):
        if obj.user and getattr(obj.user, "branch", None) and obj.user.branch.region:
            return {
                "id": obj.user.branch.region.id,
                "name": obj.user.branch.region.name,
            }
        return None

    def get_district(self, obj):
        if obj.user and getattr(obj.user, "branch", None) and obj.user.branch.district:
            return {
                "id": obj.user.branch.district.id,
                "name": obj.user.branch.district.name,
            }
        return None

    def get_branch(self, obj):
        if obj.user and getattr(obj.user, "branch", None):
            return {"id": obj.user.branch.id, "name": obj.user.branch.name}
        return None

    def get_department(self, obj):
        if obj.user and getattr(obj.user, "department", None):
            return {"id": obj.user.department.id, "name": obj.user.department.name}
        return None
