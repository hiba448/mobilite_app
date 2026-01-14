from django.db import models
from django.contrib.auth.models import User


class Filiere(models.Model):
    nom = models.CharField(max_length=255, unique=True)

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

    def __str__(self):
        return f"{self.cne} - {self.nom} {self.prenom}"


class NoteModule(models.Model):
    campagne = models.ForeignKey('mobility.Campagne', on_delete=models.CASCADE, null=True, blank=True)
    etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    note = models.FloatField()

    class Meta:
        unique_together = ('campagne', 'etudiant', 'module')

from django.db import models

class MoyenneS3(models.Model):
    etudiant = models.ForeignKey("Etudiant", on_delete=models.CASCADE, related_name="moyennes_s3")
    campagne = models.ForeignKey("mobility.Campagne", on_delete=models.CASCADE, related_name="moyennes_s3")
    moy_s3_avant_rattrapage = models.FloatField()

    class Meta:
        unique_together = ("etudiant", "campagne")

    def __str__(self):
        return f"{self.etudiant.cne} | {self.campagne} | S3={self.moy_s3_avant_rattrapage}"