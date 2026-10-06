"""Private appointment strip; never used in public badges or contact exports."""
from html import escape
import re


def appointments_html(profile):
    rows=[]
    for field,label in (("cv_check","CV-Check"),("cv_photo","CV-Foto")):
        value=str(profile.get(field) or '').strip()
        if not value:
            continue
        # Preserve the supplied slot; never invent a missing end time.
        value=re.sub(r"(\d{1,2}:\d{2}):00\b",r"\1",value)
        rows.append(f'<div><dt>{label}</dt><dd>{escape(value)}</dd></div>')
    if not rows:
        return ''
    return '<section class="personal-appointments" aria-label="Deine Termine"><strong>Deine Termine</strong><dl>'+''.join(rows)+'</dl></section>'
