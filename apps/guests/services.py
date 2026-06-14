import csv
import io
import logging
from io import BytesIO
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django.conf import settings

from .models import InvitedGuest, GuestResponse

logger = logging.getLogger(__name__)

# Tentative d'import de reportlab (optionnel)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    import qrcode
    from PIL import Image as PILImage
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed. PDF generation disabled.")


def import_guests_from_excel(excel_file, event, user):
    """
    Importe une liste d'invités depuis un fichier Excel/CSV.
    """
    import openpyxl
    
    result = {
        'created': 0,
        'errors': 0,
        'error_messages': []
    }
    
    try:
        wb = openpyxl.load_workbook(excel_file)
        ws = wb.active
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not row[0]:
                continue
            
            first_name = str(row[0]).strip() if row[0] else ''
            last_name = str(row[1]).strip() if row[1] else ''
            middle_name = str(row[2]).strip() if len(row) > 2 and row[2] else ''
            email = str(row[3]).strip() if len(row) > 3 and row[3] else ''
            phone = str(row[4]).strip() if len(row) > 4 and row[4] else ''
            
            if not first_name or not last_name:
                result['errors'] += 1
                result['error_messages'].append(f"Ligne {row_idx}: Prénom ou nom manquant")
                continue
            
            try:
                invited_guest, created = InvitedGuest.objects.get_or_create(
                    event=event,
                    email=email if email else None,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'middle_name': middle_name,
                        'phone': phone,
                        'created_by': user,
                    }
                )
                if created:
                    result['created'] += 1
                else:
                    invited_guest.first_name = first_name
                    invited_guest.last_name = last_name
                    invited_guest.middle_name = middle_name
                    invited_guest.phone = phone
                    invited_guest.save()
                    result['created'] += 1
            except Exception as e:
                result['errors'] += 1
                result['error_messages'].append(f"Ligne {row_idx}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Erreur import Excel: {str(e)}")
        result['errors'] += 1
        result['error_messages'].append(f"Erreur lecture fichier: {str(e)}")
    
    return result


def generate_invitation_pdf(guest_response):
    """
    Génère un PDF d'invitation électronique.
    Si reportlab n'est pas installé, retourne un message d'erreur.
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("reportlab is not installed. Cannot generate PDF.")
        return None
    
    event = guest_response.event
    buffer = BytesIO()
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.units import mm
        import qrcode
        from PIL import Image as PILImage
        
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        story = []
        
        # Style personnalisé
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,
            spaceAfter=20
        )
        
        # Titre
        story.append(Paragraph(f"Invitation - {event.name}", title_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Pour: {guest_response.get_full_name()}", title_style))
        story.append(Spacer(1, 20))
        
        # Informations
        info_data = [
            ["📅 Date:", event.date.strftime('%d %B %Y') if event.date else 'À confirmer'],
            ["⏰ Heure:", event.time.strftime('%H:%M') if event.time else 'À confirmer'],
            ["📍 Lieu:", event.location],
        ]
        if event.google_maps_link:
            info_data.append(["🗺️ Maps:", f'<link href="{event.google_maps_link}">Voir sur Google Maps</link>'])
        
        info_table = Table(info_data, colWidths=[80, 350])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        if event.dress_code:
            story.append(Paragraph(f"👔 Code vestimentaire: {event.dress_code}", styles['Normal']))
            story.append(Spacer(1, 10))
        
        story.append(Paragraph("Nous sommes ravis de vous compter parmi nos invités !", styles['Normal']))
        story.append(Spacer(1, 10))
        story.append(Paragraph("Veuillez confirmer votre présence via le lien reçu par email.", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # QR Code
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(guest_response.get_invitation_link())
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        qr_pil = PILImage.open(qr_buffer)
        from reportlab.lib.utils import ImageReader
        qr_reader = ImageReader(qr_pil)
        
        qr_table = Table([[Image(qr_reader, width=100*mm, height=100*mm)]])
        qr_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        story.append(qr_table)
        story.append(Spacer(1, 20))
        story.append(Paragraph("Scannez ce QR code pour confirmer votre présence", styles['Italic']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    except Exception as e:
        logger.error(f"Erreur génération PDF: {str(e)}")
        return None


def send_reminders_for_event(event, days_before=7):
    """
    Envoie des rappels aux invités qui n'ont pas encore répondu.
    """
    if not event.date:
        return 0
    
    today = datetime.now().date()
    event_date = event.date
    days_until = (event_date - today).days
    
    if days_until != days_before:
        return 0
    
    invited_guests = event.invited_guests.all()
    responded_emails = event.responses.filter(
        will_attend=True,
        verification_status='verified'
    ).values_list('email', flat=True)
    
    pending_guests = [g for g in invited_guests if g.email and g.email not in responded_emails]
    
    sent_count = 0
    for guest in pending_guests:
        try:
            response, created = GuestResponse.objects.get_or_create(
                event=event,
                email=guest.email,
                defaults={
                    'first_name': guest.first_name,
                    'last_name': guest.last_name,
                }
            )
            if response.send_reminder():
                sent_count += 1
        except Exception as e:
            logger.error(f"Erreur rappel pour {guest.email}: {str(e)}")
    
    return sent_count