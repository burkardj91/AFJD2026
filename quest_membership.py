"""Membership application and participant confirmation, with escaped HTML fields."""
from email.message import EmailMessage
from html import escape

MEMBERSHIP_NOTE = "Deine Gratismitgliedschaft gilt bis zum 31. Dezember 2027. Sie wird nicht automatisch verlängert. Im Jahr 2027 informieren wir dich und fragen dich, ob du deine Mitgliedschaft verlängern möchtest."


def application_draft(application, card):
    person=application['identity']
    msg=EmailMessage()
    msg['To']='svial@svial.ch'
    msg['Subject']=f"Gratismitgliedschaft AFJD {person['name']}" if card[2]=='membership' else f"{card[1]} · {person['name']}"
    msg['X-Unsent']='1'
    labels={'qualification':'Abschluss','study_programme':'Studiengang','address':'Postadresse','date_of_birth':'Geburtsdatum'}
    lines=['Liebes SVIAL-Team,','',f"Anmeldung von {person['name']}",f"E-Mail: {person['email']}",f"Gewinn: {card[1]}"]
    lines.extend(f'{labels[k]}: {v}' for k,v in application['details'].items() if k in labels)
    if card[2]=='membership':
        lines += ['', 'Gültig bis 31.12.2027.', MEMBERSHIP_NOTE, 'Die persönliche Bestätigung wird separat an '+person['email']+' versendet.']
    lines += ['', 'Die Person hat die Anmeldung und die Übermittlung dieser Angaben an SVIAL bestätigt.']
    msg.set_content('\n'.join(lines))
    return msg.as_bytes()


def confirmation_draft(application):
    person=application['identity']; first=person['name'].split()[0]
    msg=EmailMessage();msg['To']=person['email'];msg['Subject']='Willkommen beim SVIAL · Deine Gratismitgliedschaft';msg['X-Unsent']='1'
    msg.set_content(f'''Hallo {first},

Vielen Dank für deine Anmeldung beim SVIAL! Wir freuen uns, dich als Mitglied begrüssen zu dürfen.

{MEMBERSHIP_NOTE}

Die neusten Veranstaltungen findest du auf https://www.svial.ch/events.
Über die aktuellsten Infos informiert dich unser monatlicher Newsletter.

Möchtest du von unserem Mentoring-Programm profitieren und dich mit Expert:innen der Agro-Food-Branche für deinen nächsten Karriereschritt vernetzen? Melde dich an: https://www.svial.ch/svial-mentoring-programm/

Tritt unserer WhatsApp-Community bei: https://whatsapp.com/channel/0029Vb7wUmU7YScvg18RwD3Q
Instagram: https://www.instagram.com/svial_myagrofoodnetwork/
LinkedIn: https://www.linkedin.com/in/svial-asiat-my-agro-food-network/

Falls du Fragen hast, melde dich gerne bei uns: svial@svial.ch

Mit besten Grüssen
Dein SVIAL-Team
''')
    msg.add_alternative(f'''<!doctype html><html lang="de"><body style="margin:0;background:#f3f6f3;font-family:Arial,sans-serif;color:#183f2b"><div style="max-width:600px;margin:24px auto;background:white;padding:32px;border-top:6px solid #009641">
<p style="color:#009641;font-size:28px;font-weight:bold">svial · asiat</p>
<p>Hallo {escape(first)},</p>
<p>Vielen Dank für deine Anmeldung beim <strong>SVIAL</strong>! Wir freuen uns, dich als Mitglied begrüssen zu dürfen.</p>
<p style="background:#eef7f0;padding:18px">{MEMBERSHIP_NOTE}</p>
<p>Die neusten Veranstaltungen findest du jederzeit auf <a href="https://www.svial.ch/events">svial.ch/events</a>.<br>Für die aktuellsten Infos wirst du über unseren <strong>monatlichen Newsletter</strong> informiert.</p>
<p>Möchtest du von unserem Mentoring-Programm profitieren, bei dem du dich mit Expert:innen der Agro-Food-Branche für deinen nächsten Karriereschritt vernetzen kannst? <a href="https://www.svial.ch/svial-mentoring-programm/">Melde dich gleich zum Mentoring an.</a></p>
<p>Tritt unserer WhatsApp-Community bei:</p><p><a href="https://whatsapp.com/channel/0029Vb7wUmU7YScvg18RwD3Q" style="display:inline-block;background:#009641;color:white;padding:12px 18px;border-radius:6px;text-decoration:none;font-weight:bold">Zur WhatsApp-Community</a></p>
<p>Instagram: <a href="https://www.instagram.com/svial_myagrofoodnetwork/">@svial_myagrofoodnetwork</a><br>LinkedIn: <a href="https://www.linkedin.com/in/svial-asiat-my-agro-food-network/">SVIAL auf LinkedIn</a></p>
<p>Falls du Fragen hast, melde dich gerne bei uns: <a href="mailto:svial@svial.ch">svial@svial.ch</a></p>
<p>Mit besten Grüssen<br>Dein SVIAL-Team</p></div></body></html>''',subtype='html')
    return msg.as_bytes()
