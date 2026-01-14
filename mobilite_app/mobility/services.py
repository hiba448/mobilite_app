from django.utils import timezone

def campagne_desiderata_ouverte(campagne) -> bool:
    now = timezone.now()
    return campagne.date_ouverture_desiderata <= now <= campagne.date_cloture_desiderata