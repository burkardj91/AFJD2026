"""Original vector animal badges and accessible event celebrations."""
import base64
from html import escape

STAGES = [
    ("Curious chick", "Jede Verbindung beginnt mit einem Hallo.", "chick"),
    ("Busy bee", "Deine erste Quest ist geschafft.", "bee"),
    ("Exploring rabbit", "Neue Perspektiven eröffnen sich.", "rabbit"),
    ("Connected fox", "Noch eine Quest bis zum Gipfel.", "fox"),
    ("Alpine goat", "Gipfel erreicht. Deine Netzwerkkarte wartet auf dich.", "goat"),
]

def quest_map_html(challenges, descriptions, completed):
    """An unordered, accessible trail: every open quest remains available."""
    titles = {"Lebensmittelproduktion": "Lebensmittel entdecken", "Vernetzen": "Menschen kennenlernen",
              "Landwirtschaft": "Landwirtschaft entdecken", "Detailhandel": "Detailhandel begegnen",
              "Future Food Apéro": "Zukunft kosten", "SVIAL-Mentoring": "Mentoring entdecken"}
    icons = ["◈", "↔", "❧", "✦", "◉", "◇"]
    cards = []
    for i, quest in enumerate(challenges):
        done = quest in completed
        cards.append('<li class="quest-stop '+('is-complete' if done else '')+'"><span class="quest-stop-icon" aria-hidden="true">'+('✓' if done else icons[i % len(icons)])+'</span><div><span class="quest-stop-state">'+('Geschafft' if done else 'Noch entdecken')+'</span><h3>'+escape(titles.get(quest, quest))+'</h3><p>'+escape(descriptions[quest])+'</p></div></li>')
    return '<section class="quest-map" aria-label="Deine Quests"><p class="quest-map-hint">Dein Weg, deine Reihenfolge. Vier verschiedene Quests öffnen deine Belohnung.</p><ol class="quest-trail">'+''.join(cards)+'</ol></section>'

def animal_image(kind):
    shapes = {
        "chick": '<ellipse cx="80" cy="91" rx="39" ry="40" fill="#ef8281"/><path d="M72 51Q62 23 80 40Q93 20 90 51" fill="#ef8281"/><path d="M72 91L88 91L80 101Z" fill="#006b2d"/>',
        "bee": '<ellipse cx="58" cy="65" rx="23" ry="31" fill="#fff"/><ellipse cx="102" cy="65" rx="23" ry="31" fill="#fff"/><ellipse cx="80" cy="91" rx="30" ry="40" fill="#ef8281"/><path d="M54 89H106M56 109H104" stroke="#006b2d" stroke-width="10"/><path d="M69 52L61 37M91 52L99 37"/>',
        "rabbit": '<ellipse cx="64" cy="49" rx="13" ry="32" fill="#ef8281"/><ellipse cx="97" cy="49" rx="13" ry="32" fill="#ef8281"/><ellipse cx="80" cy="99" rx="39" ry="34" fill="#fff"/><path d="M74 109L86 109L80 116Z" fill="#ef8281"/>',
        "fox": '<path d="M40 47L73 64L87 64L120 47L113 104L80 134L47 104Z" fill="#ef8281"/><path d="M46 93L80 110L114 93L80 134Z" fill="#fff"/><path d="M74 112L86 112L80 120Z" fill="#006b2d"/>',
        "goat": '<path d="M61 67Q32 39 52 20Q48 43 72 56M99 67Q128 39 108 20Q112 43 88 56" fill="#006b2d"/><path d="M56 75L31 63L43 92M104 75L129 63L117 92" fill="#ef8281"/><path d="M80 123L72 143L88 143Z" fill="#ef8281"/><path d="M51 71Q80 51 109 71L101 114Q80 143 59 114Z" fill="#fff"/><path d="M74 115H86"/>',
    }
    eyes = '<circle cx="67" cy="85" r="3" fill="#173e2c"/><circle cx="93" cy="85" r="3" fill="#173e2c"/>'
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 160"><circle cx="80" cy="80" r="77" fill="#e7f3eb"/><g stroke="#173e2c" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">'+shapes[kind]+'</g>'+eyes+'</svg>'
    return "data:image/svg+xml;base64,"+base64.b64encode(svg.encode()).decode()

def journey_html(count):
    index = min(max(count, 0), 4)
    title, description, animal = STAGES[index]
    steps = ''.join('<div class="journey-step '+('reached' if i <= index else '')+'" '+('aria-current="step"' if i == index else '')+'><img src="'+animal_image(a)+'" alt="'+escape(t)+'"><span>'+escape(t)+'</span></div>' for i,(t,_,a) in enumerate(STAGES))
    return '<section class="journey"><div class="journey-intro"><img src="'+animal_image(animal)+'" alt="'+title+' – Illustration"><div><span class="card-kicker">DEINE AGRO-FOOD-REISE</span><h2>'+title+'</h2><p>'+description+'</p></div></div><div class="journey-trail" aria-label="Fünf Stufen; jede erfüllte Quest führt eine Stufe weiter">'+steps+'</div><p class="journey-help">'+('Besuche den SVIAL-Stand für deine Kartenziehung. Entdecke danach gerne die übrigen Quests.' if index == 4 else 'Jede neue Quest führt zum nächsten Tier. Mit vier verschiedenen Quests erreichst du Alpine goat und schaltest deine Karte frei.')+'</p></section>'

def celebration_html(title, subtitle, animal=False):
    pieces = ''.join('<i style="--x:'+str((i*29)%100)+'%;--delay:'+str((i%7)*.09)+'s;--turn:'+str(i*37)+'deg;background:'+('#009641' if i%2 else '#ef8281')+'"></i>' for i in range(30))
    return '<div class="celebration"><div class="celebration-confetti" aria-hidden="true">'+pieces+'</div>'+('<img class="summit-animal" src="'+animal_image('goat')+'" alt="Alpine goat">' if animal else '<div class="prize-star" aria-hidden="true">✦</div>')+'<span class="card-kicker">EIN MOMENT ZUM FEIERN</span><h2>'+escape(title)+'</h2><p>'+escape(subtitle)+'</p></div>'
