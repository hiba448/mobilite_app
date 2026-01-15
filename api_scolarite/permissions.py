from rest_framework.permissions import BasePermission

class IsScolarite(BasePermission):
    """
    Permission stricte : Uniquement pour le rôle 'SCOLARITE'.
    """
    def has_permission(self, request, view):
        # 1. Authentifié ?
        if not request.user or not request.user.is_authenticated:
            return False
        
        # 2. Superuser (Admin) a toujours accès
        if request.user.is_superuser:
            return True

        # 3. Vérification du rôle via le Profile
        if hasattr(request.user, 'profile'):
            return request.user.profile.role == 'SCOLARITE'
        
        return False


class IsScolariteOrSRI(BasePermission):
    """
    Permission mixte : Pour 'SCOLARITE' ou 'SRI'.
    (Je la laisse au cas où tu en aurais besoin pour des vues communes)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        if request.user.is_superuser:
            return True

        if hasattr(request.user, 'profile'):
            return request.user.profile.role in ['SCOLARITE', 'SRI']
            
        return False