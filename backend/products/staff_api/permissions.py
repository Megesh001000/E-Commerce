from rest_framework.permissions import BasePermission

class IsInventoryStaff(BasePermission):

    message = "You do not have permission to manage inventory."

    def has_permission(self,request,view):

        user=request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return (
            user.is_staff and user.groups.filter(name="InventoryStaff").exists()
        )

