"""Clustered, anonymous event graph: structural links are distinct from activity."""
from html import escape
import math
import textwrap
from quest_core import CLUSTERS


def network_html(network, counts, show_companies=False):
    centres = [(180,165),(550,165),(920,165),(330,510),(790,510)]
    organisations = network['organisations']
    groups = list(CLUSTERS)
    positions = {}
    for group,(x,y) in zip(groups,centres):
        members = [i for i,o in enumerate(organisations) if o['cluster']==group]
        for j,index in enumerate(members):
            offsets = [(0,20)] if len(members)==1 else [(-85,0),(85,0),(0,80)]
            dx,dy=offsets[j]
            positions[index] = (x+dx,y+dy)
    people=[(490+95*math.cos(i*2.39996),350+30*math.sin(i*2.39996)) for i in range(network['people'])]
    svg=['<svg viewBox="0 0 1100 700" role="img" aria-label="Five sector clusters with organisations and anonymous participant connections">']
    for label,(x,y) in zip(groups,centres):
        svg.append(f'<circle cx="{x}" cy="{y}" r="140" fill="#f1f6f2" stroke="#dce7df"/><text x="{x}" y="{y-65}" text-anchor="middle" class="cluster">{escape(label)}</text>')
    svial=next(i for i,o in enumerate(organisations) if o['connector'])
    if not show_companies:
        positions[svial]=(centres[-1][0],centres[-1][1]+72)
    sx,sy=positions[svial]
    for x,y in centres[:-1]:
        svg.append(f'<path d="M{sx} {sy} Q560 355 {x} {y}" class="structural"/>')
    for a,b in network['connections']:
        x,y=people[a];u,v=people[b]
        svg.append(f'<path d="M{x} {y} L{u} {v}" class="conversation"/>')
    visits = network['visits'] if show_companies else sorted({(a,groups.index(organisations[b]['cluster'])) for a,b in network['visits']})
    for a,b in visits:
        x,y=people[a];u,v=positions[b] if show_companies else centres[b]
        svg.append(f'<path d="M{x} {y} Q{x} {v} {u} {v}" class="visit"/>')
    for i,o in enumerate(organisations):
        if not show_companies and not o["connector"]:
            continue
        x,y=positions[i]
        name=escape(o['name'])
        label="".join(f'<tspan x="{x}" dy="{0 if j==0 else 13}">{escape(line)}</tspan>' for j,line in enumerate(textwrap.wrap(o["name"],19)))
        svg.append(f'<g><title>{name} · {o["id"]} · {escape(o["cluster"])}</title><circle cx="{x}" cy="{y}" r="{17 if o["connector"] else 11}" fill="#009641"/><text x="{x}" y="{y+30}" text-anchor="middle" class="company">{label}</text><text x="{x}" y="{y+60}" text-anchor="middle" class="id">{o["id"]}</text></g>')
    if not show_companies:
        for group,(x,y) in zip(groups,centres):
            members=[i for i,o in enumerate(organisations) if o['cluster']==group]
            count=sum(b in members for _,b in network['visits'])
            svg.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" style="font-size:35px;fill:#006b2d">{count}</text><text x="{x}" y="{y+28}" text-anchor="middle" class="company">organisation visits</text>')
    for i,(x,y) in enumerate(people):
        svg.append(f'<circle class="person" style="animation-delay:-{i*.4}s;transform-origin:{x}px {y}px" cx="{x}" cy="{y}" r="6" fill="#ef8281"/>')
    svg.append('</svg>')
    return '''<!doctype html><html><head><style>
    *{box-sizing:border-box}body{margin:0;background:#fff;color:#233a2b;font:14px Arial,sans-serif}.heading{display:flex;justify-content:space-between;align-items:center;padding:12px;border-bottom:1px solid #dce7df}button{background:white;border:1px solid #cad5cd;padding:9px 14px;border-radius:5px;cursor:pointer;color:#233a2b}svg{display:block;width:100%;max-height:480px}.cluster{font-size:18px;font-weight:600;fill:#234832}.company{font-size:12px;fill:#233a2b}.id{font-size:9px;fill:#617067}.structural{fill:none;stroke:#aabcb0;stroke-width:1.2;stroke-dasharray:5 6}.visit{fill:none;stroke:#009641;stroke-width:2;opacity:.65;stroke-dasharray:6 4;animation:flow 3s linear infinite}.conversation{fill:none;stroke:#df7373;stroke-width:2}.person{animation:breathe 3s ease-in-out infinite}.paused *{animation-play-state:paused!important}.legend{font-size:12px;color:#52685b;padding:10px 12px;line-height:1.7}.stats{display:flex;gap:35px;border-top:1px solid #dce7df;padding:15px 12px}.stats b{font-size:25px;color:#006b2d;display:block}.stats span{font-size:12px}@keyframes flow{to{stroke-dashoffset:-40}}@keyframes breathe{50%{transform:scale(1.4)}}@media(prefers-reduced-motion:reduce){*{animation:none!important}}
    </style></head><body><div class="heading"><strong>Agro-food network · live rehearsal</strong><button id="pause">Pause motion</button></div>''' + ''.join(svg)+f'''<div class="legend">Green nodes: organisations · Coral nodes: anonymous participants<br>Dashed grey: SVIAL’s illustrative ecosystem links · Green lines: recorded stand visits · Coral lines: confirmed conversations<br>Sector view aggregates links; company records remain in personal recaps. Participant identities are hidden.</div><div class="stats"><span><b>{counts['passes']}</b>Participants</span><span><b>{counts['visits']}</b>Stand visits</span><span><b>{counts['people']}</b>Conversations</span><span><b>{counts['unlocked']}</b>Cards unlocked</span></div>''' + '''<script>document.getElementById('pause').onclick=function(){const paused=document.body.classList.toggle('paused');this.textContent=paused?'Resume motion':'Pause motion';this.setAttribute('aria-pressed',String(paused));};</script></body></html>'''
