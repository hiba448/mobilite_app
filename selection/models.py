from django.db import models
from academic.models import Etudiant, Filiere
from mobility.models import Campagne, Partenaire

# =========================================================
# 1. PARAMÈTRES (Nouvelle version Singleton pour le Seuil)
# =========================================================
class ParametresSelection(models.Model):
    """
    Singleton : Stocke la configuration globale modifiable par le SRI.
    Il n'y a qu'une seule instance de ce modèle (ID=1).
    """
    seuil_eligibilite_p1 = models.FloatField(
        default=12.5, 
        verbose_name="Seuil Moyenne 1A"
    )
    seuil_admissibilite_p2 = models.FloatField(
        default=10.0, 
        verbose_name="Seuil Score Global"
    )
    # On garde les anciens champs au cas où, mais on ne s'en sert plus forcément
    min_pct = models.PositiveIntegerField(default=10, null=True, blank=True)
    max_pct = models.PositiveIntegerField(default=30, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1  # Force toujours l'ID à 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Configuration SRI (Seuils)"


# =========================================================
# 2. DOSSIER ÉTUDIANT (Version Améliorée)
# =========================================================
class DossierEtudiant(models.Model):
    """
    Contient TOUT l'historique : Admin, Eligibilité, Scores.
    """
    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)

    # --- Données Administratives (Import CSV Admin) ---
    redoublement_a1 = models.BooleanField(default=False)
    blame = models.BooleanField(default=False)

    # --- Résultats Passe 1 (Éligibilité) ---
    # ✅ AJOUTÉ : Le champ qui manquait pour le script
    eligible = models.BooleanField(null=True, blank=True)
    motif = models.CharField(max_length=255, null=True, blank=True)
    moyenne_calculee_p1 = models.FloatField(null=True, blank=True)

    # --- Données Passe 2 & 3 (Classement) ---
    moyenne_s3_avant_rattrapage = models.FloatField(null=True, blank=True)
    score_academique_p2 = models.FloatField(null=True, blank=True)
    score_global = models.FloatField(null=True, blank=True)
    classement = models.IntegerField(null=True, blank=True)

    # --- Résultat Final ---
    decision_finale = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        unique_together = ('campagne', 'etudiant')
        ordering = ['classement', '-score_global']

    def __str__(self):
        return f"Dossier {self.etudiant.cne}"


# =========================================================
# 3. ANCIENS MODÈLES (Conservés comme demandé)
# =========================================================

class ResultatPasse1(models.Model):
    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    moyenne_generale = models.FloatField(null=True, blank=True) # Renommé ou ajusté selon besoin
    moyenne_a1_sans_pfa = models.FloatField(null=True, blank=True)
    eligible = models.BooleanField(default=False)
    motif_refus = models.CharField(max_length=255, blank=True, default='')
    date_calcul = models.DateTimeField(auto_now=True)
    # Ajout d'un champ pour éviter les conflits si tu utilises est_eligible ailleurs
    est_eligible = models.BooleanField(default=False)

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"P1 {self.etudiant.cne}"

class ResultatPasse3(models.Model):
    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE, null=True, blank=True)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    note_selection = models.FloatField(null=True, blank=True)
    score_final = models.FloatField(null=True, blank=True) # Alias
    rang = models.PositiveIntegerField(null=True, blank=True)
    note_s1 = models.FloatField(null=True, blank=True)
    note_s3 = models.FloatField(null=True, blank=True)
    statut = models.CharField(
        max_length=20, default='FIFO',
        choices=[('FIFO', 'FIFO'), ('ATTENTE', 'Liste attente'), ('NON_RETENU', 'Non retenu')]
    )

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"P3 {self.etudiant.cne}"


# =========================================================
# 4. MODÈLES ÉVÉNEMENTS (Convocations / Affectations)
# =========================================================

class ConvocationEntretien(models.Model):
    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    
    date_entretien = models.DateTimeField(null=True, blank=True)
    lieu = models.CharField(max_length=255, null=True, blank=True)
    jury = models.CharField(max_length=255, null=True, blank=True)
    
    statut_convocation = models.CharField(max_length=50, default="CONVOQUE") 
    message = models.TextField(null=True, blank=True)

    # Résultats fusionnés
    est_present = models.BooleanField(default=False)
    note_entretien = models.FloatField(null=True, blank=True)
    commentaire = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Convocation {self.etudiant.cne}"

class ResultatEntretien(models.Model):
    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    present = models.BooleanField(default=True)
    score = models.FloatField(default=0)
    commentaire = models.TextField(null=True, blank=True)
    decision = models.CharField(
        max_length=20, default='EN_ATTENTE',
        choices=[('VALIDE', 'Validé'), ('REFUSE', 'Refusé'), ('EN_ATTENTE', 'En attente')]
    )

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"Oral {self.etudiant.cne}"

class AffectationFinale(models.Model):
    campagne = models.ForeignKey(Campagne, on_delete=models.CASCADE)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    partenaire = models.ForeignKey(Partenaire, on_delete=models.SET_NULL, null=True, blank=True)
    type_mobilite = models.CharField(
        max_length=2, choices=[('EC', 'Echange'), ('DD', 'Double Diplome')],
        null=True, blank=True
    )
    choix_obtenu = models.PositiveIntegerField(null=True, blank=True)
    statut = models.CharField(
        max_length=50, default='NON_PUBLIE',
        choices=[
            ('AFFECTE', 'Affecté'),
            ('LISTE_ATTENTE', 'Liste d\'attente'),
            ('NON_RETENU', 'Non retenu'),
            ('NON_PUBLIE', 'Non publié'),
            ('DESISTEMENT', 'Désistement'),
        ]
    )

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"Affectation {self.etudiant.cne}"