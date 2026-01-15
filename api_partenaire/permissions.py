from rest_framework.permissions import BasePermission

class IsPartenaire(BasePermission):
    """
    Vérifie que l'utilisateur a le rôle 'PARTENAIRE'.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'profile') and
            request.user.profile.role == 'PARTENAIRE'
        )