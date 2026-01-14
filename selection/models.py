from django.db import models


class ParametresSelection(models.Model):
    """
    Paramètres globaux par campagne:
    SEUIL1 = 12.5
    SEUIL2 = 13.5 (peut être ajusté dynamiquement ensuite)
    min_pct = 10%
    max_pct = 30%
    """
    campagne = models.OneToOneField('mobility.Campagne', on_delete=models.CASCADE)
    seuil1 = models.FloatField(default=12.5)
    seuil2 = models.FloatField(default=13.5)
    min_pct = models.PositiveIntegerField(default=10)
    max_pct = models.PositiveIntegerField(default=30)

    def __str__(self):
        return f"Params {self.campagne}"


class DossierEtudiant(models.Model):
    """
    Porte les infos nécessaires aux critères C1.1, C1.2 et à la passe 3 (S3).
    """
    campagne = models.ForeignKey('mobility.Campagne', on_delete=models.CASCADE)
    etudiant = models.ForeignKey('academic.Etudiant', on_delete=models.CASCADE)

    # Passe 1
    redoublement_a1 = models.BooleanField(default=False)   # C1.1
    blame = models.BooleanField(default=False)             # C1.2

    # Passe 3 (critère S3 avant rattrapage)
    moyenne_s3_avant_rattrapage = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"Dossier {self.etudiant.cne} ({self.campagne})"


class ResultatPasse1(models.Model):
    campagne = models.ForeignKey('mobility.Campagne', on_delete=models.CASCADE)
    etudiant = models.ForeignKey('academic.Etudiant', on_delete=models.CASCADE)

    moyenne_a1_sans_pfa = models.FloatField()
    eligible = models.BooleanField(default=False)
    motif_refus = models.CharField(max_length=255, blank=True, default='')

    date_calcul = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"P1 {self.etudiant.cne} eligible={self.eligible}"


class ResultatPasse3(models.Model):
    campagne = models.ForeignKey('mobility.Campagne', on_delete=models.CASCADE)
    filiere = models.ForeignKey('academic.Filiere', on_delete=models.CASCADE)
    etudiant = models.ForeignKey('academic.Etudiant', on_delete=models.CASCADE)

    note_selection = models.FloatField()
    rang = models.PositiveIntegerField(null=True, blank=True)
    note_s1 = models.FloatField(null=True, blank=True)
    note_s3 = models.FloatField(null=True, blank=True)

    # Statut avant oral (FIFO / attente / non retenu)
    statut = models.CharField(
        max_length=20,
        default='FIFO',
        choices=[
            ('FIFO', 'FIFO'),
            ('ATTENTE', 'Liste attente'),
            ('NON_RETENU', 'Non retenu'),
        ],
    )

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"P3 {self.etudiant.cne} note={self.note_selection}"


class ConvocationEntretien(models.Model):
    campagne = models.ForeignKey('mobility.Campagne', on_delete=models.CASCADE)
    etudiant = models.ForeignKey('academic.Etudiant', on_delete=models.CASCADE)
    
    # Ajoutez ces champs s'ils manquent :
    date_entretien = models.DateTimeField(null=True, blank=True)
    lieu = models.CharField(max_length=255, null=True, blank=True)
    
    # ✅ AJOUT POUR LE SCRIPT PASSE 4
    statut_convocation = models.CharField(max_length=50, default="CONVOQUE") 
    message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Convocation {self.etudiant} - {self.statut_convocation}"

class ResultatEntretien(models.Model):
    campagne = models.ForeignKey('mobility.Campagne', on_delete=models.CASCADE)
    etudiant = models.ForeignKey('academic.Etudiant', on_delete=models.CASCADE)

    present = models.BooleanField(default=True)
    
    # ✅ AJOUTS POUR LE DASHBOARD COMITÉ
    score = models.FloatField(default=0)  # Note sur 20 (Motivation)
    commentaire = models.TextField(null=True, blank=True) # Avis du jury

    # Champs booléens optionnels (vous pouvez les garder si vous voulez)
    engagement_financier_ok = models.BooleanField(default=False)
    motivation_ok = models.BooleanField(default=False)

    decision = models.CharField(
        max_length=20,
        default='EN_ATTENTE',
        # On aligne les choix avec ce que le Front envoie (VALIDE / REFUSE)
        choices=[
            ('VALIDE', 'Validé'),
            ('REFUSE', 'Refusé'),
            ('EN_ATTENTE', 'En attente'),
        ],
    )

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"Oral {self.etudiant.cne} {self.decision}"


class AffectationFinale(models.Model):
    campagne = models.ForeignKey('mobility.Campagne', on_delete=models.CASCADE)
    etudiant = models.ForeignKey('academic.Etudiant', on_delete=models.CASCADE)

    partenaire = models.ForeignKey('mobility.Partenaire', on_delete=models.SET_NULL, null=True, blank=True)
    type_mobilite = models.CharField(
        max_length=2,
        choices=[('EC', 'Echange'), ('DD', 'Double Diplome')],
        null=True, blank=True
    )
    choix_obtenu = models.PositiveIntegerField(null=True, blank=True)

    statut = models.CharField(
        max_length=20,
        default='NON_PUBLIE',
        choices=[
            ('AFFECTE', 'Affecte'),
            ('LISTE_ATTENTE', 'Liste attente'),
            ('NON_RETENU', 'Non retenu'),
            ('NON_PUBLIE', 'Non publie'),
            ('CONVOQUE', 'Convoqué Entretien'),     # ✅ Ajouté pour cohérence
            ('ADMIS_DEFINITIF', 'Admis Définitif'), # ✅ Ajouté pour la finalisation
        ],
    )

    class Meta:
        unique_together = ('campagne', 'etudiant')

    def __str__(self):
        return f"Final {self.etudiant.cne} {self.statut}"