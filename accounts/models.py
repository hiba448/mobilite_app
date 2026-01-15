from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        SCOLARITE = "SCOLARITE", "Scolarite"
        SRI = "SRI", "SRI"
        PARTENAIRE = "PARTENAIRE", "Partenaire"
        CF = "CF", "Coordinateur Filiere"
        COMITE = "COMITE", "Comite Selection"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    # Pour les Coordinateurs de Filière (CF)
    filiere = models.ForeignKey(
        "academic.Filiere",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # ✅ AJOUT DU CHAMP MANQUANT (Pour les Partenaires)
    partenaire = models.OneToOneField(
        "mobility.Partenaire",  # On utilise le string pour éviter les erreurs d'import
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profile_partenaire"
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"