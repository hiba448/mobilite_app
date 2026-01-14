import csv
import io

from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from mobility.models import Campagne
from academic.models import Etudiant, Module, NoteModule, MoyenneS3  # adapte si noms diffèrent
from .permissions import IsScolariteOrSRI


def get_active_campagne():
    return Campagne.objects.filter(active=True).first()


@api_view(["POST"])
@permission_classes([IsScolariteOrSRI])
def upload_notes_csv(request):
    """
    CSV attendu: cne,nom_mod,note
    """
    campagne = get_active_campagne()
    if not campagne:
        return Response({"detail": "Aucune campagne active."}, status=400)

    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "Fichier manquant (champ 'file')."}, status=400)

    data = f.read().decode("utf-8-sig")  # gère BOM
    reader = csv.DictReader(io.StringIO(data))

    required = {"cne", "nom_mod", "note"}
    if not required.issubset(set([h.strip() for h in reader.fieldnames or []])):
        return Response({"detail": f"Colonnes requises: {sorted(required)}"}, status=400)

    created, updated, errors = 0, 0, []

    with transaction.atomic():
        for i, row in enumerate(reader, start=2):  # ligne 1 = header
            try:
                cne = (row.get("cne") or "").strip()
                nom_mod = (row.get("nom_mod") or "").strip()
                note_raw = (row.get("note") or "").strip().replace(",", ".")

                if not cne or not nom_mod or note_raw == "":
                    raise ValueError("Valeur vide")

                note = float(note_raw)
                if note < 0 or note > 20:
                    raise ValueError("Note hors [0..20]")

                etu = Etudiant.objects.filter(cne=cne).first()
                if not etu:
                    raise ValueError(f"Etudiant introuvable: {cne}")

                mod, _ = Module.objects.get_or_create(nom=nom_mod)

                obj, was_created = NoteModule.objects.update_or_create(
                    etudiant=etu,
                    module=mod,
                    campagne=campagne,   # si ton modèle NoteModule a campagne
                    defaults={"note": note},
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors.append({"line": i, "error": str(e), "row": row})

    return Response(
        {"ok": True, "created": created, "updated": updated, "errors": errors},
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsScolariteOrSRI])
def upload_s3_csv(request):
    """
    CSV attendu: cne,moy_s3_avant_rattrapage
    """
    campagne = get_active_campagne()
    if not campagne:
        return Response({"detail": "Aucune campagne active."}, status=400)

    f = request.FILES.get("file")
    if not f:
        return Response({"detail": "Fichier manquant (champ 'file')."}, status=400)

    data = f.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(data))

    required = {"cne", "moy_s3_avant_rattrapage"}
    if not required.issubset(set([h.strip() for h in reader.fieldnames or []])):
        return Response({"detail": f"Colonnes requises: {sorted(required)}"}, status=400)

    created, updated, errors = 0, 0, []

    with transaction.atomic():
        for i, row in enumerate(reader, start=2):
            try:
                cne = (row.get("cne") or "").strip()
                moy_raw = (row.get("moy_s3_avant_rattrapage") or "").strip().replace(",", ".")

                if not cne or moy_raw == "":
                    raise ValueError("Valeur vide")

                moy = float(moy_raw)
                if moy < 0 or moy > 20:
                    raise ValueError("Moyenne hors [0..20]")

                etu = Etudiant.objects.filter(cne=cne).first()
                if not etu:
                    raise ValueError(f"Etudiant introuvable: {cne}")

                obj, was_created = MoyenneS3.objects.update_or_create(
                    etudiant=etu,
                    campagne=campagne,
                    defaults={"moy_s3_avant_rattrapage": moy},
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

            except Exception as e:
                errors.append({"line": i, "error": str(e), "row": row})

    return Response(
        {"ok": True, "created": created, "updated": updated, "errors": errors},
        status=status.HTTP_200_OK
    )