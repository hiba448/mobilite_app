from statistics import median
from academic.models import MoyenneS3

def mediane_s3_filiere(campagne, filiere_obj) -> float | None:
    """
    Retourne la médiane des moyennes S3 (avant rattrapage) pour une filière donnée et une campagne.
    filiere_obj = l'objet Filiere (pas juste le nom).
    """
    qs = MoyenneS3.objects.filter(
        campagne=campagne,
        etudiant__filiere=filiere_obj
    ).values_list("moy_s3_avant_rattrapage", flat=True)

    values = list(qs)
    if not values:
        return None
    return float(median(values))