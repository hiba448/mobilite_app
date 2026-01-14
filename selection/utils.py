from academic.models import MoyenneS3

def mediane_s3_filiere(campagne, filiere):
    """
    Calcule la médiane des moyennes S3 pour une filière donnée et une campagne.
    Retourne un float ou None si pas de données.
    """
    # On récupère toutes les moyennes S3 de la filière pour cette campagne
    # Note: On utilise filter(etudiant__filiere=filiere)
    moyennes = MoyenneS3.objects.filter(
        campagne=campagne, 
        etudiant__filiere=filiere
    ).values_list('moy_s3_avant_rattrapage', flat=True).order_by('moy_s3_avant_rattrapage')

    # Conversion en float et nettoyage des None
    notes = [float(n) for n in moyennes if n is not None]
    count = len(notes)

    if count == 0:
        return None

    # Calcul médiane mathématique
    if count % 2 == 1:
        # Nombre impair : on prend la valeur du milieu
        return notes[count // 2]
    else:
        # Nombre pair : moyenne des deux valeurs centrales
        lower = notes[count // 2 - 1]
        upper = notes[count // 2]
        return (lower + upper) / 2.0