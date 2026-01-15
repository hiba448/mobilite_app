from django.db import models
from django.contrib.auth.models import User

class Filiere(models.Model):
    nom = models.CharField(max_length=255, unique=True)
    
    
    # ✅ AJOUT PHASE 3 : Effectif total pour le calcul des 10% et 30%
    nombre_inscrits_2a = models.PositiveIntegerField(
        default=0, 
        help_text="Nombre total d'étudiants inscrits en 2ème année (Base des Quotas)"
    )

    def __str__(self):
        return self.nom


class Module(models.Model):
    nom = models.CharField(max_length=255)
    is_tc = models.BooleanField(default=False)        # ✅ module commun TC
    is_specialite = models.BooleanField(default=False)
    is_pfa = models.BooleanField(default=False)

    def __str__(self):
        return self.nom


class Etudiant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cne = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=255)
    prenom = models.CharField(max_length=255)
    filiere = models.ForeignKey(Filiere, on_delete=models.CASCADE)
    
    # --- Champs existants (Passe 1) ---
    moyenne_generale = models.FloatField(default=0.0) # Utile pour l'éligibilité Passe 1
    
    # ✅ AJOUTS PHASE 3 : Stockage des moyennes pour le calcul du Score et Filtre S3
    moyenne_s3 = models.FloatField(null=True, blank=True, help_text="Moyenne S3 (Filtre)")
    
    moyenne_1a_tc = models.FloatField(null=True, blank=True, help_text="Moyenne Tronc Commun")
    moyenne_1a_spec = models.FloatField(null=True, blank=True, help_text="Moyenne Spécialité")
    
    # Le score final calculé : (0.8 * TC) + (0.2 * SPEC)
    # db_index=True accélère le tri lors du classement
    score_selection = models.FloatField(null=True, blank=True, db_index=True)

    def __str__(self):
        return f"{self.cne} - {self.nom} {self.prenom}"

    def save(self, *args, **kwargs):
        # ✅ CALCUL AUTOMATIQUE DU SCORE
        # Dès qu'on sauvegarde l'étudiant, si les notes sont là, on met à jour le score.
        
        if self.moyenne_1a_tc is not None and self.moyenne_1a_spec is not None:
            self.score_selection = round((0.8 * self.moyenne_1a_tc) + (0.2 * self.moyenne_1a_spec), 3)
        super().save(*args, **kwargs)


class NoteModule(models.Model):
    campagne = models.ForeignKey('mobility.Campagne', on_delete=models.CASCADE, null=True, blank=True)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    note = models.FloatField()

    class Meta:
        unique_together = ('campagne', 'etudiant', 'module')

# On garde ton modèle MoyenneS3 pour l'historique par campagne si tu le souhaites,
# mais pour l'algo actif, on utilisera le champ 'moyenne_s3' directement dans Etudiant.
class MoyenneS3(models.Model):
    etudiant = models.ForeignKey("Etudiant", on_delete=models.CASCADE, related_name="moyennes_s3_history")
    campagne = models.ForeignKey("mobility.Campagne", on_delete=models.CASCADE, related_name="moyennes_s3")
    moy_s3_avant_rattrapage = models.FloatField()

    class Meta:
        unique_together = ("etudiant", "campagne")

    def __str__(self):
        return f"{self.etudiant.cne} | {self.campagne} | S3={self.moy_s3_avant_rattrapage}"