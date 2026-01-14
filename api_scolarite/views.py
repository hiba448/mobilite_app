import csv
import io
from django.db import transaction
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from academic.models import Etudiant, Module, NoteModule
from selection.models import DossierEtudiant
from mobility.models import Campagne

# --- FONCTIONS UTILITAIRES ---

def get_active_campagne():
    return Campagne.objects.filter(active=True).first()

def parse_bool(value):
    """
    Transforme n'importe quelle entrée (OUI, oui, Yes, 1, True) en Booléen Python.
    Retourne False par défaut.
    """
    if not value:
        return False
    clean_val = str(value).strip().upper()
    return clean_val in ['OUI', 'TRUE', '1', 'YES', 'Y', 'VRAI']

# =========================================================
# 1. IMPORT INFOS ADMINISTRATIVES (Redoublement / Blâme)
# =========================================================
@api_view(["POST"])
@permission_classes([AllowAny]) 
@parser_classes([MultiPartParser, FormParser])
def import_admin_csv(request):
    """
    Fichier attendu : infos_admin.csv
    Colonnes : CNE;Redoublant_1A;Blame
    Action : Met à jour (force) les statuts administratifs.
    """
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({"error": "Aucun fichier fourni."}, status=400)

    campagne = get_active_campagne()
    if not campagne:
        return Response({"error": "Aucune campagne active."}, status=400)

    try:
        # 1. Lecture avec nettoyage du BOM (utf-8-sig)
        decoded_file = file_obj.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file, delimiter=';')
        
        # 2. Nettoyage des noms de colonnes (enlève les espaces autour)
        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]

        # 3. Vérification basique
        if 'CNE' not in reader.fieldnames:
            return Response({"error": f"Colonne 'CNE' introuvable. Colonnes lues : {reader.fieldnames}"}, status=400)

        updated_count = 0
        errors = []

        print("--- DÉBUT IMPORT ADMIN ---")

        with transaction.atomic():
            for i, row in enumerate(reader, start=1):
                cne = row.get('CNE', '').strip()
                if not cne: continue # Ligne vide

                etudiant = Etudiant.objects.filter(cne=cne).first()
                if not etudiant:
                    # errors.append(f"Ligne {i}: CNE {cne} introuvable.")
                    continue

                # Lecture des valeurs
                raw_red = row.get('Redoublant_1A', '')
                raw_blame = row.get('Blame', '')
                
                is_red = parse_bool(raw_red)
                has_blame = parse_bool(raw_blame)

                # DEBUG : On affiche les changements critiques
                if is_red or has_blame:
                    print(f"🔴 ADMIN {cne} -> Redoublant: {is_red} | Blâme: {has_blame}")

                # MISE À JOUR STRICTE (update_or_create)
                # On force la valeur lue dans le fichier
                dossier, created = DossierEtudiant.objects.update_or_create(
                    campagne=campagne,
                    etudiant=etudiant,
                    defaults={
                        'redoublement_a1': is_red,
                        'blame': has_blame
                    }
                )
                updated_count += 1

        print(f"--- FIN IMPORT ADMIN : {updated_count} dossiers traités ---")
        return Response({
            "message": f"Succès : {updated_count} dossiers administratifs mis à jour.",
            "errors": errors
        }, status=200)

    except Exception as e:
        print(f"ERREUR CRITIQUE ADMIN: {e}")
        return Response({"error": str(e)}, status=500)


# =========================================================
# 2. IMPORT NOTES (Académique pur)
# =========================================================
@api_view(["POST"])
@permission_classes([AllowAny]) 
@parser_classes([MultiPartParser, FormParser])
def import_notes_csv(request):
    """
    Fichier attendu : notes.csv
    Colonnes : CNE;Nom_Module;Type_Module;Note
    Action : Ajoute les notes, crée le dossier si inexistant (mais SANS toucher aux flags admin).
    """
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({"error": "Aucun fichier fourni."}, status=400)

    campagne = get_active_campagne()
    if not campagne:
        return Response({"error": "Aucune campagne active."}, status=400)

    try:
        decoded_file = file_obj.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file, delimiter=';')
        
        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]

        count_notes = 0
        errors = []

        print("--- DÉBUT IMPORT NOTES ---")

        with transaction.atomic():
            for i, row in enumerate(reader, start=1):
                cne = row.get('CNE', '').strip()
                if not cne: continue

                etudiant = Etudiant.objects.filter(cne=cne).first()
                if not etudiant:
                    continue

                try:
                    note_val = float(row['Note'].replace(',', '.'))
                    mod_nom = row['Nom_Module'].strip()
                    type_mod = row['Type_Module'].upper().strip()
                except ValueError:
                    errors.append(f"Ligne {i}: Erreur format note pour {cne}")
                    continue

                # 1. Dossier : On s'assure qu'il existe, MAIS ON NE L'ÉCRASE PAS
                # get_or_create ne touchera pas à redoublement_a1 ni blame s'ils existent déjà
                DossierEtudiant.objects.get_or_create(
                    campagne=campagne, 
                    etudiant=etudiant
                )

                # 2. Module
                module, _ = Module.objects.get_or_create(
                    nom=mod_nom,
                    defaults={
                        'is_pfa': (type_mod == 'PFA'),
                        'is_tc': (type_mod == 'TC'),
                        'is_specialite': (type_mod == 'SPEC')
                    }
                )

                # 3. Note
                NoteModule.objects.update_or_create(
                    campagne=campagne, etudiant=etudiant, module=module,
                    defaults={'note': note_val}
                )
                count_notes += 1

        print(f"--- FIN IMPORT NOTES : {count_notes} notes traitées ---")
        return Response({
            "message": f"Succès : {count_notes} notes importées.", 
            "errors": errors
        }, status=200)

    except Exception as e:
        print(f"ERREUR CRITIQUE NOTES: {e}")
        return Response({"error": str(e)}, status=500)


# =========================================================
# 3. IMPORT S3 (Passe 3)
# =========================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def upload_s3_csv(request):
    """
    Format : cne,moy_s3_avant_rattrapage (virgule ou point-virgule acceptés)
    """
    campagne = get_active_campagne()
    if not campagne: return Response({"detail": "Aucune campagne active."}, status=400)

    f = request.FILES.get("file")
    if not f: return Response({"detail": "Fichier manquant."}, status=400)

    try:
        data = f.read().decode("utf-8-sig")
        # Petite astuce pour gérer virgule ET point-virgule
        if ';' in data.splitlines()[0]:
            reader = csv.DictReader(io.StringIO(data), delimiter=';')
        else:
            reader = csv.DictReader(io.StringIO(data), delimiter=',')

        # Nettoyage header
        if reader.fieldnames:
            reader.fieldnames = [name.strip() for name in reader.fieldnames]

        updated = 0
        with transaction.atomic():
            for row in reader:
                # On cherche la clé insensible à la casse
                cne_key = next((k for k in row.keys() if k.lower() == 'cne'), None)
                moy_key = next((k for k in row.keys() if 'moy' in k.lower()), None)

                if not cne_key or not moy_key: continue

                cne = row[cne_key].strip()
                moy_raw = row[moy_key].strip().replace(",", ".")

                if cne and moy_raw:
                    etu = Etudiant.objects.filter(cne=cne).first()
                    if etu:
                        DossierEtudiant.objects.update_or_create(
                            etudiant=etu, campagne=campagne,
                            defaults={"moyenne_s3_avant_rattrapage": float(moy_raw)}
                        )
                        updated += 1
        
        return Response({"ok": True, "created": updated}, status=200)
    except Exception as e:
        return Response({"detail": str(e)}, status=500)


# =========================================================
# 4. ROUTE OBSOLÈTE (Pour éviter les crashs d'URL)
# =========================================================
@api_view(["POST"])
@permission_classes([AllowAny])
def upload_notes_csv_old(request):
    return Response({"detail": "Cette route n'existe plus. Utilisez import-csv."}, status=400)