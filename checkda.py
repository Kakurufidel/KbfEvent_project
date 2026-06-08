from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.events.models import Event, EventCollaborator

User = get_user_model()


class Command(BaseCommand):
    help = 'Verifie les utilisateurs, evenements et co-organisateurs'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('        VERIFICATION DE LA BASE DE DONNEES'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # 1. Utilisateurs
        self.stdout.write('\n[1] UTILISATEURS')
        users = User.objects.all()
        self.stdout.write(f'Total utilisateurs: {users.count()}')
        
        for user in users:
            self.stdout.write(f'  - ID: {user.id} | Email: {user.email} | Nom: {user.first_name} {user.last_name} | Superuser: {user.is_superuser}')
        
        # 2. Evenements
        self.stdout.write('\n[2] EVENEMENTS')
        events = Event.objects.all()
        self.stdout.write(f'Total evenements: {events.count()}')
        
        for event in events:
            self.stdout.write(f'  - ID: {event.id} | Nom: {event.name}')
            self.stdout.write(f'    Date: {event.date} | Lieu: {event.location[:50] if event.location else "Non defini"}')
            self.stdout.write(f'    Organisateur: {event.main_organizer.email if event.main_organizer else "AUCUN"}')
            self.stdout.write(f'    Slug: {event.slug}')
            self.stdout.write(f'    RSVP token: {event.rsvp_token}')
            self.stdout.write(f'    Statut: {"Actif" if event.is_active else "Inactif"}')
        
        # 3. Verification des evenements sans organisateur
        orphan_events = Event.objects.filter(main_organizer__isnull=True)
        if orphan_events.exists():
            self.stdout.write(self.style.WARNING(f'\n  ATTENTION: {orphan_events.count()} evenement(s) sans organisateur !'))
        
        # 4. Co-organisateurs
        self.stdout.write('\n[3] CO-ORGANISATEURS')
        collaborators = EventCollaborator.objects.all()
        self.stdout.write(f'Total invitations: {collaborators.count()}')
        
        for collab in collaborators:
            status_color = self.style.SUCCESS if collab.status == 'accepted' else self.style.WARNING
            self.stdout.write(f'  - Evenement: {collab.event.name}')
            self.stdout.write(f'    Utilisateur: {collab.user.email if collab.user else "Inconnu"}')
            self.stdout.write(status_color(f'    Statut: {collab.status}'))
        
        # 5. Resume pour le dashboard
        self.stdout.write('\n[4] RESUME POUR LE DASHBOARD')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        for user in users:
            owned = Event.objects.filter(main_organizer=user)
            collaborating = Event.objects.filter(collaborators__user=user, collaborators__status='accepted')
            
            self.stdout.write(f'\nUtilisateur: {user.email}')
            self.stdout.write(f'  - Evenements cree: {owned.count()}')
            for e in owned:
                self.stdout.write(f'      * {e.name}')
            self.stdout.write(f'  - Co-organisateur de: {collaborating.count()}')
            for e in collaborating:
                self.stdout.write(f'      * {e.name}')
        
        # 6. Test de connexion
        self.stdout.write('\n[5] TEST DE CONNEXION RECOMMANDE')
        self.stdout.write('Pour vous connecter, utilisez un des emails ci-dessus.')
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('        VERIFICATION TERMINEE'))
        self.stdout.write(self.style.SUCCESS('=' * 60))