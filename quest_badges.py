"""Fill the supplied two-page, ten-label Word template without rebuilding styles."""
from copy import deepcopy
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E

TEMPLATE = Path(__file__).with_name('assets') / 'badge-template.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
CONTENT_TOP_TWIPS = 567  # 10 mm below every label's top edge.
QR_SIZE_EMU = 1408430
QR_SIZE_TWIPS = QR_SIZE_EMU / 635
INLINE_TOP_TWIPS = -4  # Word inline-image offset from the cell content reference.

REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS = {'w':W,'a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}


def fit_badge_text(first, last, institution):
    """Explicit line wrapping within the 32 mm text column and 39 mm QR height."""
    from PIL import ImageFont
    def font(bold):
        for name in (["arialbd.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"] if bold else ["arial.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]):
            try: return ImageFont.truetype(name, 400)
            except OSError: pass
        return ImageFont.load_default(size=400)
    fonts = [font(True), font(True), font(False)]
    def wrap(text, size, face):
        words = str(text or '').split()
        lines = []; line = ''
        def fits(value): return face.getlength(value) / 400 * size <= 84
        for word in words:
            if line and not fits(line+' '+word): lines.append(line); line=''
            while not fits(word):
                cut = len(word)-1
                while cut > 1 and not fits(word[:cut]): cut -= 1
                if line: lines.append(line); line=''
                lines.append(word[:cut]); word=word[cut:]
            line = (line+' '+word).strip()
        if line: lines.append(line)
        return lines or ['']
    for half_points in range(32, 15, -1):
        sizes = [half_points/2, half_points/2, min(13, half_points/2)]
        # Prefer smaller type over tearing an ordinary word apart. Only truly
        # exceptional words are split once the readable minimum is reached.
        if half_points > 16 and any(face.getlength(word)/400*size > 84
                for text,size,face in zip((first,last,institution),sizes,fonts)
                for word in str(text or '').split()):
            continue
        blocks = [(wrap(text, size, face),size) for text,size,face in zip((first,last,institution),sizes,fonts)]
        height = sum(len(lines)*size*1.2 for lines,size in blocks)+4
        if height <= 98:
            return blocks
    raise ValueError("Name oder Institution ist zu lang für einen lesbaren Badge. Bitte die Badge-Bezeichnung kürzen.")


def _node(parent, tag, **attributes):
    return E.SubElement(parent, '{'+W+'}'+tag, {'{'+W+'}'+k:str(v) for k,v in attributes.items()})


def _cell_layout(cell, top=0):
    props=cell.find('w:tcPr',NS)
    for child in list(props):
        if E.QName(child).localname in {'tcMar','vAlign'}: props.remove(child)
    margins=_node(props,'tcMar')
    for side,value in [('top',top),('left',411),('right',0),('bottom',0)]:
        _node(margins,side,w=value,type='dxa')
    _node(props,'vAlign',val='top')
    for child in list(cell):
        if child is not props: cell.remove(child)


def _paragraph(parent, lines, size, bold=False, after=0):
    paragraph=_node(parent,'p'); props=_node(paragraph,'pPr')
    _node(props,'spacing',before=0,after=after,line=round(size*1.2*20),lineRule='exact')
    _node(props,'ind',left=0,right=0)
    _node(props,'jc',val='left')
    run=_node(paragraph,'r'); rp=_node(run,'rPr')
    _node(rp,'rFonts',ascii='Arial',hAnsi='Arial')
    _node(rp,'sz',val=round(size*2))
    if bold: _node(rp,'b')
    for index,line in enumerate(lines):
        if index: _node(run,'br')
        _node(run,'t').text=line or '\u00a0'
    return paragraph


def qr_visible_top(image_bytes):
    """White quiet zone remains intact; compensate its height in the layout."""
    from PIL import Image
    image=Image.open(BytesIO(image_bytes)).convert('L')
    bounds=image.point(lambda pixel:255 if pixel < 100 else 0).getbbox()
    if bounds is None: raise ValueError("Das QR-Bild enthält keinen sichtbaren Code.")
    return round(bounds[1] / image.height * QR_SIZE_TWIPS) + INLINE_TOP_TWIPS


def fit_front_cell(cell, first, last, institution, qr_top):
    blocks=fit_badge_text(first,last,institution)
    first_size=next((size for lines,size in blocks if any(line.strip() for line in lines)),16)
    text_top=max(1, qr_top-round(first_size*4.25))
    anchor=deepcopy(next(a for a in cell.findall('.//wp:anchor',NS)
        if any(b.get('{'+R+'}embed')=='rId4' for b in a.findall('.//a:blip',NS))))
    inline=E.Element('{'+NS['wp']+'}inline',distT='0',distB='0',distL='0',distR='0')
    for name in ('extent','effectExtent','docPr','cNvGraphicFramePr'):
        child=anchor.find('wp:'+name,NS)
        if child is not None: inline.append(deepcopy(child))
    inline.find('wp:extent',NS).set('cx','1408430')
    inline.find('wp:extent',NS).set('cy','1408430')
    inline.append(deepcopy(anchor.find('a:graphic',NS)))
    _cell_layout(cell, top=CONTENT_TOP_TWIPS-qr_top)
    table=_node(cell,'tbl'); props=_node(table,'tblPr')
    _node(props,'tblW',w=4132,type='dxa'); _node(props,'tblLayout',type='fixed')
    _node(props,'tblInd',w=0,type='dxa')
    borders=_node(props,'tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'): _node(borders,edge,val='nil')
    grid=_node(table,'tblGrid')
    for width in (1914,2218): _node(grid,'gridCol',w=width)
    row=_node(table,'tr')
    for index,width in enumerate((1914,2218)):
        target=_node(row,'tc'); cp=_node(target,'tcPr'); _node(cp,'tcW',w=width,type='dxa')
        margins=_node(cp,'tcMar')
        for edge,value in [('top',0),('left',0),('right',114 if index==0 else 0),('bottom',0)]:
            _node(margins,edge,w=value,type='dxa')
        _node(cp,'vAlign',val='top')
        if index==0:
            spacer=_paragraph(target,[''],1)
            spacer.find('w:pPr/w:spacing',NS).set('{'+W+'}line',str(text_top))
            for i,(lines,size) in enumerate(blocks):
                if not any(line.strip() for line in lines): continue
                _paragraph(target,lines,size,bold=i<2,after=80 if i==1 else 0)
            if target.find('w:p',NS) is None: _paragraph(target,[''],1)
        else:
            paragraph=_paragraph(target,[],1)
            spacing=paragraph.find('w:pPr/w:spacing',NS)
            spacing.set('{'+W+'}line','240'); spacing.set('{'+W+'}lineRule','auto')
            drawing=_node(paragraph.find('w:r',NS),'drawing'); drawing.append(inline)
    _paragraph(cell,[''],1)


def fit_back_cell(cell, person):
    _cell_layout(cell, top=CONTENT_TOP_TWIPS-round(16*4.25))
    _paragraph(cell,['ID: '+person['id']],16,True,after=120)
    _paragraph(cell,['Zugangscode:'],12,True,after=20)
    _paragraph(cell,[person['code']],10,after=40)
    label=person.get('provisional_name') or person.get('name','')
    # The private side identifies the assigned person or the reserve slot.
    for lines,size in fit_badge_text('','',label)[2:]:
        _paragraph(cell,lines,min(size,10))


@lru_cache(maxsize=512)
def qr_image(value):
    import qrcode
    from PIL import Image, ImageDraw
    import cv2
    import numpy as np
    logo_source = Image.open(Path(__file__).with_name('assets') / 'svial-logo-rgb.png').convert('RGBA')
    detector = cv2.QRCodeDetector()
    # The centre logo can affect some QR masks: validate before printing.
    for mask in range(8):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=4, box_size=10, mask_pattern=mask)
        qr.add_data(value)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        logo = logo_source.copy()
        width = round(image.width * .15)
        logo.thumbnail((width, width), Image.Resampling.LANCZOS)
        x, y = (image.width-logo.width)//2, (image.height-logo.height)//2
        ImageDraw.Draw(image).rectangle((x-6,y-6,x+logo.width+6,y+logo.height+6),fill='white')
        image.paste(logo,(x,y),logo)
        if all(detector.detectAndDecode(np.array(sample))[0] == value for sample in (image, image.resize((300,300),Image.Resampling.LANCZOS))):
            stream = BytesIO()
            image.save(stream, format='PNG')
            return stream.getvalue()
    raise ValueError("Kein lesbarer QR-Code mit Logo erzeugt. Versuche eine kürzere öffentliche App-Adresse.")


def badge_docx(roster, people, base_url, mirror_backs=True, qr_encoder=qr_image):
    if not people:
        raise ValueError('Wähle mindestens eine Person.')
    with ZipFile(TEMPLATE) as source:
        parts = {name:source.read(name) for name in source.namelist()}
    root = E.fromstring(parts['word/document.xml'])
    # Keep the required trailing paragraph to one twip so the exact A4 grid fits.
    for paragraph in root.findall('w:body/w:p',NS):
        for child in list(paragraph):paragraph.remove(child)
        properties=E.SubElement(paragraph,'{'+W+'}pPr')
        spacing=E.SubElement(properties,'{'+W+'}spacing')
        for key,value in {'before':'0','after':'0','line':'1','lineRule':'exact'}.items():spacing.set('{'+W+'}'+key,value)
    relationships = E.fromstring(parts['word/_rels/document.xml.rels'])
    table = root.find('.//w:body/w:tbl',NS)
    # A4: badges at x=15..100 mm and 110..195 mm; 10 mm centre gutter.
    # Five 55 mm rows start at y=12 mm and end at 287 mm (10 mm bottom).
    margins = root.find('.//w:sectPr/w:pgMar',NS)
    for side,value in {'top':680,'bottom':567,'left':850,'right':850}.items():
        margins.set('{'+W+'}'+side,str(value))
    table.find('w:tblPr/w:tblW',NS).set('{'+W+'}w','10205')
    position = table.find('w:tblPr/w:tblpPr',NS)
    table.find('w:tblPr',NS).remove(position)
    table.find('w:tblPr/w:tblLayout',NS).set('{'+W+'}type','fixed')
    grid = table.find('w:tblGrid',NS)
    for column in list(grid):grid.remove(column)
    for width in (4819,567,4819):E.SubElement(grid,'{'+W+'}gridCol').set('{'+W+'}w',str(width))
    for row in table.findall('w:tr',NS):
        row.find('w:trPr/w:trHeight',NS).set('{'+W+'}val','3118')
        row.find('w:trPr/w:trHeight',NS).set('{'+W+'}hRule','exact')
        _node(row.find('w:trPr',NS),'cantSplit')
        for index,cell in enumerate(row.findall('w:tc',NS)):
            cell.find('w:tcPr/w:tcW',NS).set('{'+W+'}w','567' if index==1 else '4819')
            if index==1:
                _cell_layout(cell)
                for margin in cell.findall('w:tcPr/w:tcMar/*',NS): margin.set('{'+W+'}w','0')
                _paragraph(cell,[''],1)
    prototypes = [deepcopy(row) for row in table.findall('w:tr',NS)]
    for row in table.findall('w:tr',NS): table.remove(row)
    for start in range(0,len(people),10):
        batch = people[start:start+10]
        for back in (False, True):
            for row_index in range(5):
                row = deepcopy(prototypes[row_index + (5 if back else 0)])
                for col,cell in enumerate(row.findall('w:tc',NS)[::2]):
                    index = row_index*2 + ((1-col) if back and mirror_backs else col)
                    if index >= len(batch):
                        for child in list(cell):
                            if child.tag != '{'+W+'}tcPr':cell.remove(child)
                        E.SubElement(cell,'{'+W+'}p')
                        continue
                    token = batch[index]; person = roster[token]
                    if back:
                        fit_back_cell(cell, person)
                    else:
                        # The QR contains the only visible logo; remove every template logo.
                        for drawing in list(cell.findall('.//w:drawing',NS)):
                            if any(b.get('{'+R+'}embed') == 'rId5' for b in drawing.findall('.//a:blip',NS)):
                                drawing.getparent().remove(drawing)
                        for paragraph in cell.findall('w:p',NS):
                            if paragraph.findall('.//w:t',NS):
                                properties=paragraph.find('w:pPr',NS)
                                if properties is None:
                                    properties=E.Element('{'+W+'}pPr');paragraph.insert(0,properties)
                                alignment=properties.find('w:jc',NS)
                                if alignment is None:alignment=E.SubElement(properties,'{'+W+'}jc')
                                alignment.set('{'+W+'}val','left')
                        first = person.get('first_name')
                        last = person.get('last_name')
                        if first is None or last is None:
                            first, _, last = person['name'].partition(' ')
                        if person.get('blank_badge'): first, last = '\u00a0', '\u00a0'
                        values={'Vorname':first,'Nachname':last,'Institution':person.get('affiliation','')}
                        for text in cell.findall('.//w:t',NS):
                            if text.text in values:text.text=values[text.text]
                        qr_bytes=qr_encoder(base_url.rstrip('/')+'/?badge='+token)
                        fit_front_cell(cell, first, last, person.get('affiliation',''), qr_visible_top(qr_bytes))
                        image_name=f'badge-qr-{start+index}.png';rid=f'rIdBadge{start+index}'
                        parts['word/media/'+image_name]=qr_bytes
                        E.SubElement(relationships,'{'+REL+'}Relationship',Id=rid,Type=R+'/image',Target='media/'+image_name)
                        for blip in cell.findall('.//a:blip',NS):
                            if blip.get('{'+R+'}embed')=='rId4':blip.set('{'+R+'}embed',rid)
                table.append(row)
    # A separate fixed five-row table per page prevents cumulative pagination drift.
    body=root.find('w:body',NS)
    rows=list(table.findall('w:tr',NS))
    insertion=list(body).index(table)
    body.remove(table)
    for offset in range(0,len(rows),5):
        page=deepcopy(table)
        for old in list(page.findall('w:tr',NS)): page.remove(old)
        for row in rows[offset:offset+5]: page.append(row)
        if offset:
            separator=E.Element('{'+W+'}p'); pp=_node(separator,'pPr')
            _node(pp,'spacing',before=0,after=0,line=1,lineRule='exact')
            _node(_node(separator,'r'),'br',type='page')
            body.insert(insertion,separator); insertion+=1
        body.insert(insertion,page); insertion+=1
    for index,element in enumerate(root.findall('.//wp:docPr',NS),1):element.set('id',str(index))
    # Optional Word editing identifiers must remain unique after row cloning.
    for index,element in enumerate(root.iter(),1):
        for key in list(element.attrib):
            if E.QName(key).localname in {'paraId','anchorId','editId'}:element.set(key,f'{index:08X}')
    parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
    parts['word/_rels/document.xml.rels']=E.tostring(relationships,xml_declaration=True,encoding='UTF-8',standalone=True)
    output=BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for name,data in parts.items():archive.writestr(name,data)
    return output.getvalue()
