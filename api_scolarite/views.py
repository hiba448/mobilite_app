import csv
import io
from django.db import transaction
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from academic.models import Etudiant, Module, NoteModule, Filiere
from selection.models import DossierEtudiant
from mobility.models import Campagne
from .permissions import IsScolarite

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
# 1. GESTION DES EFFECTIFS
# =========================================================
@api_view(['GET', 'POST'])
@permission_classes([IsScolarite])
def manage_effectifs(request):
    """
    GET: Renvoie la liste des filières et leur effectif 2A.
    POST: Met à jour les effectifs.
    """
    if request.method == 'GET':
        data = Filiere.objects.all().values('id', 'nom', 'nombre_inscrits_2a').order_by('nom')
        return Response(list(data))

    elif request.method == 'POST':
        # Attend une liste: [{ "id": 1, "nombre": 60 }, { "id": 2, "nombre": 55 }]
        updates = request.data.get('updates', [])
        count = 0
        for item in updates:
            try:
                fil = Filiere.objects.get(id=item['id'])
                fil.nombre_inscrits_2a = int(item['nombre'])
                fil.save()
                count += 1
            except:
                continue
        return Response({"message": f"{count} effectifs mis à jour !"}, status=200)


# =========================================================
# 2. IMPORT NOTES S3 (CSV Simple)
# =========================================================
@api_view(['POST'])
@permission_classes([IsScolarite])
def import_notes_s3(request):
    """
    CSV attendu : CNE;Moyenne_S3
    """
    file = request.FILES.get('file')
    if not file: return Response({"detail": "Fichier manquant"}, 400)

    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.reader(decoded_file, delimiter=';')
    
    updated = 0
    errors = 0

    for row in reader:
        try:
            # Skip header si présent
            if "CNE" in row[0].upper(): continue
            
            cne = row[0].strip()
            note_s3 = float(row[1].replace(',', '.'))
            
            etu = Etudiant.objects.filter(cne=cne).first()
            if etu:
                etu.moyenne_s3 = note_s3
                etu.save()
                updated += 1
        except Exception:
            errors += 1

    return Response({
        "message": f"Moyennes S3 importées : {updated} succès, {errors} erreurs."
    })


# =========================================================
# 3. IMPORT NOTES 1A & CALCUL SCORE (CSV Complexe)
# =========================================================
# =========================================================
# 3. IMPORT NOTES 1A & CALCUL SCORE (CSV Complexe)
# =========================================================
@api_view(['POST'])
@permission_classes([IsScolarite])
def import_notes_1a(request):
    """
    CSV attendu : CNE;Nom_Module;Type_Module;Note
    Type_Module : 'TC', 'SPEC' ou 'PFA'
    """
    file = request.FILES.get('file')
    if not file: 
        return Response({"detail": "Fichier manquant"}, status=400)

    campagne = get_active_campagne()
    if not campagne:
        return Response({"error": "Aucune campagne active."}, status=400)

    try:
        decoded_file = file.read().decode('utf-8-sig').splitlines()
        reader = csv.reader(decoded_file, delimiter=';')

        data_temp = {}  # Pour moyennes TC/SPEC
        errors = []
        line_count = 0
        header_skipped = False

        print("\n--- DÉBUT IMPORT NOTES 1A ---")

        with transaction.atomic():
            for i, row in enumerate(reader, start=1):
                print(f"\n🔍 Ligne {i}: {row}")
                
                try:
                    # Skip si ligne vide
                    if not row or len(row) == 0:
                        print(f"   ⏭ Ligne vide")
                        continue
                    
                    if len(row) < 4:
                        print(f"   ⚠ Ligne incomplète ({len(row)} colonnes)")
                        errors.append(f"Ligne {i}: seulement {len(row)} colonnes")
                        continue
                    
                    # Skip Header UNIQUEMENT LA PREMIÈRE FOIS
                    first_cell = str(row[0]).strip().upper()
                    if not header_skipped and ("CNE" == first_cell or "ETUDIANT" in first_cell):
                        print(f"   📋 Header ignoré")
                        header_skipped = True
                        continue
                    
                    cne = row[0].strip()
                    nom_module = row[1].strip()
                    type_mod = row[2].strip().upper()
                    note_raw = row[3].strip()
                    
                    print(f"   CNE='{cne}' | Module='{nom_module}' | Type='{type_mod}' | Note='{note_raw}'")
                    
                    # Vérification CNE non vide
                    if not cne:
                        print(f"   ⚠ CNE vide")
                        continue
                    
                    # Conversion de la note
                    try:
                        note = float(note_raw.replace(',', '.'))
                    except ValueError:
                        print(f"   ❌ Note invalide: '{note_raw}'")
                        errors.append(f"Ligne {i}: Note invalide '{note_raw}'")
                        continue
                    
                    print(f"   ✓ Note convertie: {note}")
                    
                    # Récupération de l'étudiant
                    etu = Etudiant.objects.filter(cne=cne).first()
                    if not etu:
                        print(f"   ❌ CNE '{cne}' introuvable")
                        errors.append(f"Ligne {i}: CNE '{cne}' introuvable")
                        continue
                    
                    # === NOUVEAU : Création du Module et de la Note ===
                    module, _ = Module.objects.get_or_create(
                        nom=nom_module,
                        defaults={
                            'is_pfa': (type_mod == 'PFA'),
                            'is_tc': (type_mod == 'TC'),
                            'is_specialite': (type_mod == 'SPEC')
                        }
                    )
                    
                    # Création/Mise à jour de la note dans NoteModule
                    NoteModule.objects.update_or_create(
                        campagne=campagne,
                        etudiant=etu,
                        module=module,
                        defaults={'note': note}
                    )
                    print(f"   💾 NoteModule créée/mise à jour")
                    # === FIN NOUVEAU ===
                    
                    # Initialisation du dict pour calcul moyennes TC/SPEC
                    if cne not in data_temp:
                        data_temp[cne] = {"TC": [], "SPEC": [], "etudiant": etu}
                    
                    # Ajout de la note selon le type (pour calcul moyennes)
                    if type_mod in ["TC", "SPEC"]:
                        data_temp[cne][type_mod].append(note)
                        line_count += 1
                        print(f"   ✅ Ajouté: {cne} -> {type_mod} = {note}")
                    elif type_mod == "PFA":
                        line_count += 1
                        print(f"   ✅ PFA ajouté: {cne} = {note}")
                    else:
                        print(f"   ⚠ Type invalide '{type_mod}' (attendu: TC, SPEC ou PFA)")
                        
                except Exception as e:
                    errors.append(f"Ligne {i}: {str(e)}")
                    print(f"   ❌ Erreur: {e}")

            print(f"\n{'=' * 80}")
            print(f"RÉSUMÉ PARSING :")
            print(f"  Lignes de notes traitées : {line_count}")
            print(f"  Étudiants uniques : {len(data_temp)}")
            print(f"{'=' * 80}\n")

            # Calcul des moyennes TC/SPEC et sauvegarde dans Etudiant
            updated_count = 0
            
            print("CALCUL MOYENNES TC/SPEC :")
            
            for cne, data in data_temp.items():
                etu = data["etudiant"]
                notes_tc = data["TC"]
                notes_spec = data["SPEC"]
                
                print(f"\n🔍 CNE: '{cne}'")
                updated = False
                
                # Calcul Moyenne TC
                if notes_tc:
                    moy_tc = sum(notes_tc) / len(notes_tc)
                    etu.moyenne_1a_tc = round(moy_tc, 3)
                    updated = True
                    print(f"   📊 Moyenne TC: {moy_tc:.3f} (sur {len(notes_tc)} notes)")
                
                # Calcul Moyenne SPEC
                if notes_spec:
                    moy_spec = sum(notes_spec) / len(notes_spec)
                    etu.moyenne_1a_spec = round(moy_spec, 3)
                    updated = True
                    print(f"   📊 Moyenne SPEC: {moy_spec:.3f} (sur {len(notes_spec)} notes)")
                
                if updated:
                    etu.save()
                    updated_count += 1
                    print(f"   💾 Étudiant sauvegardé")

            print(f"\n{'=' * 80}")
            print(f"RÉSULTAT FINAL : {updated_count} étudiants mis à jour")
            print(f"{'=' * 80}")

        response_data = {
            "message": f"Notes 1A traitées pour {updated_count} étudiants. Scores calculés.",
            "details": {
                "lignes_traitees": line_count,
                "etudiants_uniques": len(data_temp),
                "etudiants_mis_a_jour": updated_count
            }
        }
        
        if errors:
            response_data["errors"] = errors[:20]

        return Response(response_data, status=200)

    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()
        return Response({"detail": str(e)}, status=500)
# =========================================================
# 4. IMPORT INFOS ADMINISTRATIVES (Redoublement / Blâme)
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
# 5. IMPORT NOTES (Académique pur)
# =========================================================
'''
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
'''