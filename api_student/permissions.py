from rest_framework.permissions import BasePermission

class IsStudent(BasePermission):
    """
    Permission permettant l'accès uniquement aux étudiants connectés.
    """
    def has_permission(self, request, view):
        # On vérifie que l'utilisateur est authentifié et qu'il a un profil Étudiant
        return bool(
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'etudiant')
        )