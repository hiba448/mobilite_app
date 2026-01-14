from django.db import models


class Campagne(models.Model):
    annee = models.CharField(max_length=9, unique=True)  # ex: 2025-2026
    date_ouverture_desiderata = models.DateTimeField()
    date_cloture_desiderata = models.DateTimeField()
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.annee


class Partenaire(models.Model):
    nom_ecole = models.CharField(max_length=255, unique=True)
    pays = models.CharField(max_length=100)

    def __str__(self):
        return self.nom_ecole


class OffrePartenaire(models.Model):
    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    partenaire = models.ForeignKey(Partenaire, on_delete=models.CASCADE)
    filiere_origine = models.ForeignKey('academic.Filiere', on_delete=models.CASCADE)
    filiere_accueil = models.CharField(max_length=255)
    nb_places_ec = models.PositiveIntegerField(default=0)
    nb_places_dd = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('campagne', 'partenaire', 'filiere_origine', 'filiere_accueil')

    def __str__(self):
        return f"{self.partenaire} - {self.filiere_origine} ({self.campagne})"


class Desiderata(models.Model):
    TYPE_CHOIX = [
        ('EC', 'Echange'),
        ('DD', 'Double Diplome'),
    ]

    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    etudiant = models.ForeignKey('academic.Etudiant', on_delete=models.CASCADE)
    partenaire = models.ForeignKey(Partenaire, on_delete=models.CASCADE)
    filiere_accueil = models.CharField(max_length=255)
    type_mobilite = models.CharField(max_length=2, choices=TYPE_CHOIX)
    priorite = models.PositiveIntegerField()
    statut = models.CharField(
        max_length=20,
        default='EN_ATTENTE',
        choices=[
            ('EN_ATTENTE', 'En attente'),
            ('VALIDE', 'Validé'),
            ('REFUSE', 'Refusé'),
        ],
    )
    date_saisie = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ('campagne', 'etudiant', 'priorite')
        ordering = ['priorite']

    def __str__(self):
        return f"{self.etudiant.cne} - choix {self.priorite}"
    
    def save(self, *args, **kwargs):
        from mobility.services import campagne_desiderata_ouverte
        if not campagne_desiderata_ouverte(self.campagne):
            raise ValueError("Deadline dépassée: desiderata figés (Règle 2.1.2).")
        super().save(*args, **kwargs)
class Alignement(models.Model):
    """
    Matrice d'alignement pédagogique : quelles filières d'accueil sont autorisées
    pour une filière ENSIAS donnée, chez un partenaire, et pour quel type (EC/DD).
    """
    TYPE_CHOIX = [
        ('EC', 'Echange'),
        ('DD', 'Double Diplome'),
    ]

    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    filiere_origine = models.ForeignKey('academic.Filiere', on_delete=models.CASCADE)
    partenaire = models.ForeignKey(Partenaire, on_delete=models.CASCADE)
    filiere_accueil = models.CharField(max_length=255)
    type_mobilite = models.CharField(max_length=2, choices=TYPE_CHOIX)

    class Meta:
        unique_together = ('campagne', 'filiere_origine', 'partenaire', 'filiere_accueil', 'type_mobilite')

    def __str__(self):
        return f"{self.filiere_origine} -> {self.partenaire} ({self.type_mobilite})"
    


class DecisionPartenaire(models.Model):
    class Decision(models.TextChoices):
        ACCEPTE = "ACCEPTE", "Accepté"
        REFUSE = "REFUSE", "Refusé"
        EN_ATTENTE = "EN_ATTENTE", "En attente"

    campagne = models.ForeignKey("mobility.Campagne", on_delete=models.CASCADE)
    partenaire = models.ForeignKey("mobility.Partenaire", on_delete=models.CASCADE)
    etudiant = models.ForeignKey("academic.Etudiant", on_delete=models.CASCADE)

    decision = models.CharField(max_length=20, choices=Decision.choices, default=Decision.EN_ATTENTE)
    commentaire = models.TextField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("campagne", "partenaire", "etudiant")

    def __str__(self):
        return f"{self.partenaire} - {self.etudiant} - {self.decision}"