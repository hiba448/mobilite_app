from django.core.management.base import BaseCommand
from academic.models import NoteModule, Etudiant
from mobility.models import Campagne

class Command(BaseCommand):
    help = "Diagnostic des notes pour CNE001"

    def handle(self, *args, **options):
        campagne = Campagne.objects.filter(active=True).first()
        if not campagne:
            self.stdout.write(self.style.ERROR("Aucune campagne active"))
            return

        etu = Etudiant.objects.filter(cne="CNE001").first()
        if not etu:
            self.stdout.write(self.style.ERROR("CNE001 introuvable"))
            return

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(f"DIAGNOSTIC NOTES POUR {etu.cne} - {etu.nom} {etu.prenom}")
        self.stdout.write(f"{'='*80}\n")

        # Toutes les notes
        toutes_notes = NoteModule.objects.filter(campagne=campagne, etudiant=etu)
        self.stdout.write(f"📊 TOUTES LES NOTES ({toutes_notes.count()}) :")
        for note in toutes_notes:
            self.stdout.write(
                f"   {note.module.nom:40} | Note: {note.note:5.2f} | "
                f"TC: {note.module.is_tc} | SPEC: {note.module.is_specialite} | PFA: {note.module.is_pfa}"
            )

        # Notes sans PFA
        notes_sans_pfa = NoteModule.objects.filter(
            campagne=campagne, 
            etudiant=etu, 
            module__is_pfa=False
        )
        
        self.stdout.write(f"\n📊 NOTES SANS PFA ({notes_sans_pfa.count()}) :")
        total = 0
        count = 0
        for note in notes_sans_pfa:
            self.stdout.write(f"   {note.module.nom:40} | Note: {note.note:5.2f}")
            total += note.note
            count += 1
        
        if count > 0:
            moyenne_calculee = total / count
            self.stdout.write(f"\n✅ MOYENNE CALCULÉE : {moyenne_calculee:.2f}")
            self.stdout.write(f"   Somme: {total} / Nombre: {count}")
        
        self.stdout.write(f"\n{'='*80}\n")