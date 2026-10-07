"""Private appointment strip; never used in public badges or contact exports."""
from html import escape
import re


def appointment_slots(profile):
    slots=[]
    for field,label in (("cv_check","CV-Check"),("cv_photo","CV-Foto")):
        value=str(profile.get(field) or '').strip()
        if value.casefold() in {"", "nan", "nat", "none", "null", "<na>", "n/a"}:
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


def render_appointment_details(profile):
    import streamlit as st
    for label, value in appointment_slots(profile):
        with st.container(border=True):
            st.markdown("**" + label + "**")
            st.text(value)
    if appointment_slots(profile):
        st.caption("Deine persönlichen Zeitfenster · Bitte sei pünktlich vor Ort.")
    with st.container(border=True):
        st.markdown("**Flying Apéro Future Food**")
        st.text("Ab 18 Uhr · Für alle")


def render_appointments(profile):
    import streamlit as st
    slots = appointment_slots(profile)
    with st.container(key="personal-appointments"):
        with st.expander("Deine Termine" + (" · " + " & ".join(label for label, _ in slots) if slots else " · Flying Apéro"), expanded=False):
            render_appointment_details(profile)
