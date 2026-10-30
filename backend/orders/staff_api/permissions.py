from rest_framework.permissions import BasePermission

class IsOrderStaff(BasePermission):
    message = "You do not have permission to access order management."

    def has_permission(self,request,view):
        user=request.user

        if not user or  not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return (
            user.is_staff and user.groups.filter(
                name__in=["OrderManage","WarehouseStaff"]
            ).exists()
        )