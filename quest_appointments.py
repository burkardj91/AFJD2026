"""Private appointment strip; never used in public badges or contact exports."""
from html import escape
import re


def appointment_slots(profile):
    slots=[]
    for field,label in (("cv_check","CV-Check"),("cv_photo","CV-Foto")):
        value=str(profile.get(field) or '').strip()
        if not value:
            continue
        # Preserve the supplied slot; never invent a missing end time.
        value=re.sub(r"(\d{1,2}:\d{2}):00\b",r"\1",value)
        slots.append((label, value))
    return slots


def appointments_html(profile):
    rows = [f'<div><dt>{label}</dt><dd>{escape(value)}</dd></div>' for label, value in appointment_slots(profile)]
    if not rows:
        return ''
    return '<section class="personal-appointments" aria-label="Deine Termine"><strong>Deine Termine</strong><dl>'+''.join(rows)+'</dl></section>'


def render_appointments(profile):
    """Native Streamlit elements, visible without HTML definition-list rendering."""
    import streamlit as st
    slots = appointment_slots(profile)
    if not slots:
        return
    with st.container(border=True, key="personal-appointments"):
        st.subheader("Deine gebuchten Termine")
        for label, value in slots:
            with st.container(border=True):
                st.markdown("**" + label + "**")
                st.text(value)
        st.caption("Deine persönlichen Zeitfenster · Bitte sei pünktlich vor Ort.")
