"""Read-only reward status for the personal pass."""
def reward_status(quest, person):
    card=next((c for c,owner in quest.assignments.items() if owner==person),None)
    if card in quest.applications or card in quest.collected:
        return "redeemed", "Gewinn eingelöst", card
    if card:
        return "reserved", "Gewinn erhalten · Jetzt einlösen", card
    if person in quest.unlocked:
        return "unlocked", "Netzwerkkarte freigeschaltet", None
    return "exploring", "Entdecke die Veranstaltung", None
