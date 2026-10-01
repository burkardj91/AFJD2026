"""Public welcome screen, using the supplied AFJD event poster."""
import base64
from pathlib import Path

POSTER = Path(__file__).with_name('assets') / 'afjd-poster-2026.webp'

def welcome_html():
    image = base64.b64encode(POSTER.read_bytes()).decode('ascii')
    return '''<style>
.afjd-welcome{display:grid;grid-template-columns:minmax(150px,.8fr) minmax(0,1.2fr);align-items:center;gap:36px;margin:12px 0 28px}
.afjd-welcome img{display:block;width:100%;height:auto;max-height:440px;object-fit:contain}
.afjd-welcome .eyebrow{color:var(--accent);font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin:0 0 12px}
.afjd-welcome h1{font-size:clamp(26px,3.5vw,42px)!important;line-height:1.12!important;letter-spacing:-.025em;margin:0 0 18px!important;padding:0!important}
.afjd-welcome p{font-size:17px;line-height:1.6;color:var(--ink)}
.afjd-welcome .event-details{border-top:1px solid var(--line);padding-top:16px;margin-top:22px;font-size:15px}
.afjd-welcome .event-details strong{display:block}
@media(max-width:600px){.afjd-welcome{grid-template-columns:105px minmax(0,1fr);gap:18px;align-items:start;margin:8px 0 22px}.afjd-welcome h1{font-size:26px!important;margin-bottom:12px!important}.afjd-welcome .eyebrow{font-size:10px;margin-bottom:8px}.afjd-welcome p{font-size:14px;line-height:1.5}.afjd-welcome .event-details{font-size:13px;padding-top:10px;margin-top:12px}}
@media(max-width:360px){.afjd-welcome{grid-template-columns:80px minmax(0,1fr);gap:12px}.afjd-welcome h1{font-size:23px!important}}
</style><section class="afjd-welcome" aria-label="Willkommen beim Agro-Food Job Dating">
<img src="data:image/webp;base64,'''+image+'''" width="1137" height="1600" alt="Plakat Agro-Food Job Dating 2026: Meet. Connect. Start your career. 8. Oktober, Technopark. Veranstaltet von SVIAL mit Partnern und Unterstützern.">
<div><p class="eyebrow">Agro-Food Job Dating · 2026</p><h1>Dein Abend.<br>Deine Kontakte.<br>Deine Chancen.</h1><p>Schön, dass du dabei bist! Lerne Menschen aus der Agro-Food-Branche kennen, entdecke Unternehmen und schalte mit deinen Networking-Quests Gewinne frei.</p><p class="event-details"><strong>Donnerstag, 8. Oktober 2026 · ab 17 Uhr</strong>Technopark · Deinen persönlichen Zugangscode erhältst du am Welcome Desk.</p></div></section>'''
