"""Local brand assets; no external image or font requests."""
from pathlib import Path
from functools import lru_cache
import base64

LOGO_PATH = Path(__file__).with_name("assets") / "svial-logo-rgb.png"

@lru_cache(maxsize=1)
def logo_uri():
    return "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")

def masthead():
    return '<div class="masthead"><img class="brand-logo" src="'+logo_uri()+'" alt="SVIAL ASIAT"><div class="event-label"><strong>Agro-Food Job Dating</strong><span>Network Quest · 2026</span></div></div>'
