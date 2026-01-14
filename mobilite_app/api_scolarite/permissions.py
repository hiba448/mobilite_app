from rest_framework.permissions import BasePermission

def in_group(user, name: str) -> bool:
    return user and user.is_authenticated and user.groups.filter(name=name).exists()

class IsScolariteOrSRI(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return in_group(u, "SCOLARITE") or in_group(u, "SRI") or u.is_superuser