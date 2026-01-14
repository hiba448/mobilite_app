from rest_framework.permissions import BasePermission

class IsSRI(BasePermission):
    """
    Autorise seulement les users du groupe SRI (ou superuser).
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name="SRI").exists()