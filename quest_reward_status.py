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


def reward_avatar_html(state, card, image, stage):
    from html import escape
    from urllib.parse import urlencode
    avatar='<img src="'+escape(image,quote=True)+'" alt="'+escape(stage,quote=True)+'">'
    if state == "reserved" and card:
        href='?'+urlencode({'claim':card})
        label="Deinen Gewinn einlösen"
    elif state == "unlocked":
        href='?invitation=1'
        label="Deine Netzwerkkarten-Einladung anzeigen"
    else:
        return avatar
    return '<a class="reward-avatar-link" href="'+escape(href,quote=True)+'" target="_self" aria-label="'+label+'" title="'+label+'">'+avatar+'</a>'
