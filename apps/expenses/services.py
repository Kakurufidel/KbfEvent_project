from decimal import Decimal
from django.db.models import Count, Q, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from collections import defaultdict
from apps.guests.models import GuestResponse, InvitedGuest
from .models import BeveragePack


class EstimationService:
    """
    Service pour calculer l'estimation des besoins en boissons
    """

    def __init__(self, event, include_pending=True, attendance_rate=0.75):
        self.event = event
        self.include_pending = include_pending
        self.attendance_rate = attendance_rate
        self._cache = {}

    def get_drink_choices(self):
        """
        Récupère tous les choix de boissons des invités ayant confirmé leur présence
        """
        # Récupérer les réponses avec will_attend=True
        responses = GuestResponse.objects.filter(
            event=self.event,
            will_attend=True
        ).only('drink_choice', 'drink_other', 'is_accompanied', 'number_of_guests')

        choices = defaultdict(int)

        for response in responses:
            # Compter l'invité lui-même
            if response.drink_choice and response.drink_choice != 'other':
                choices[response.drink_choice] += 1
            elif response.drink_choice == 'other' and response.drink_other:
                choices[response.drink_other] += 1

            # Compter les accompagnants
            if response.is_accompanied:
                if response.companion_drink_choice and response.companion_drink_choice != 'other':
                    choices[response.companion_drink_choice] += response.number_of_guests - 1
                elif response.companion_drink_choice == 'other' and response.companion_drink_other:
                    choices[response.companion_drink_other] += response.number_of_guests - 1

        return dict(choices)

    def get_pending_estimation(self, existing_choices):
        """
        Estime les choix des invités qui n'ont pas encore répondu
        """
        if not self.include_pending:
            return {}

        # Invités pré-enregistrés qui n'ont pas encore répondu
        responded_emails = GuestResponse.objects.filter(
            event=self.event
        ).values_list('email', flat=True)

        pending_count = InvitedGuest.objects.filter(
            event=self.event
        ).exclude(
            email__in=responded_emails
        ).count()

        if pending_count == 0 or not existing_choices:
            return {}

        # Estimation basée sur la répartition des choix existants
        total_existing = sum(existing_choices.values())
        if total_existing == 0:
            return {}

        pending_choices = {}
        for drink, count in existing_choices.items():
            proportion = count / total_existing
            estimated = int(pending_count * self.attendance_rate * proportion)
            if estimated > 0:
                pending_choices[drink] = estimated

        return pending_choices

    def calculate_needs(self):
        """
        Calcule les besoins en packs pour chaque boisson
        """
        # 1. Récupérer les choix existants
        existing_choices = self.get_drink_choices()

        # 2. Estimer les choix des invités en attente
        pending_choices = self.get_pending_estimation(existing_choices)

        # 3. Agréger tous les choix
        all_choices = defaultdict(int)
        for drink, count in existing_choices.items():
            all_choices[drink] += count
        for drink, count in pending_choices.items():
            all_choices[drink] += count

        # 4. Récupérer les packs configurés
        packs = BeveragePack.objects.filter(event=self.event, is_active=True)

        result = []
        total_cost = Decimal('0')
        total_packs = 0

        for pack in packs:
            drink_name = pack.drink_name
            needed_units = all_choices.get(drink_name, 0)

            # Calculer le nombre de packs nécessaires (arrondi supérieur)
            if needed_units > 0:
                packs_needed = (needed_units + pack.pack_quantity - 1) // pack.pack_quantity
                cost = packs_needed * pack.pack_price
                total_cost += cost
                total_packs += packs_needed
            else:
                packs_needed = 0
                cost = Decimal('0')

            result.append({
                'drink_name': drink_name,
                'needed_units': needed_units,
                'pack_quantity': pack.pack_quantity,
                'packs_needed': packs_needed,
                'pack_price': pack.pack_price,
                'unit_price': pack.unit_price(),
                'cost': cost,
                'unit_type': pack.unit_type,
                'is_active': pack.is_active,
            })

        return {
            'details': result,
            'total_cost': total_cost,
            'total_packs': total_packs,
            'total_units': sum(all_choices.values()),
            'existing_choices': dict(existing_choices),
            'pending_choices': dict(pending_choices),
            'pending_guests_count': sum(pending_choices.values()) if pending_choices else 0,
        }

    def get_chart_data(self):
        """
        Prépare les données pour les graphiques
        """
        choices = self.get_drink_choices()
        if not choices:
            return {'labels': [], 'data': [], 'colors': []}

        # Trier par ordre décroissant
        sorted_choices = sorted(choices.items(), key=lambda x: x[1], reverse=True)

        # Couleurs pour le graphique
        colors = [
            '#8B5CF6', '#06B6D4', '#F59E0B', '#10B981',
            '#EF4444', '#EC4899', '#6366F1', '#14B8A6'
        ]

        return {
            'labels': [item[0] for item in sorted_choices[:8]],
            'data': [item[1] for item in sorted_choices[:8]],
            'colors': colors[:len(sorted_choices)]
        }