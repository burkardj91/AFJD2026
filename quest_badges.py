"""Fill the supplied two-page, ten-label Word template without rebuilding styles."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E

TEMPLATE = Path(__file__).with_name('assets') / 'badge-template.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS = {'w':W,'a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'}


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
    # Word requires a paragraph after the table; keep it within the 2 mm remainder.
    for paragraph in root.findall('w:body/w:p',NS):
        for child in list(paragraph):paragraph.remove(child)
        properties=E.SubElement(paragraph,'{'+W+'}pPr')
        spacing=E.SubElement(properties,'{'+W+'}spacing')
        for key,value in {'before':'0','after':'0','line':'20','lineRule':'exact'}.items():spacing.set('{'+W+'}'+key,value)
    relationships = E.fromstring(parts['word/_rels/document.xml.rels'])
    table = root.find('.//w:body/w:tbl',NS)
    # A4: 20 mm side margins; 2 x 85 mm labels, 5 x 55 mm rows.
    # 10 mm top margin leaves 12 mm below the 275 mm grid.
    margins = root.find('.//w:sectPr/w:pgMar',NS)
    for side,value in {'top':567,'bottom':567,'left':1134,'right':1134}.items():
        margins.set('{'+W+'}'+side,str(value))
    table.find('w:tblPr/w:tblW',NS).set('{'+W+'}w','9638')
    position = table.find('w:tblPr/w:tblpPr',NS)
    position.set('{'+W+'}tblpY','567')
    grid = table.find('w:tblGrid',NS)
    for column in list(grid):grid.remove(column)
    for _ in range(2):E.SubElement(grid,'{'+W+'}gridCol').set('{'+W+'}w','4819')
    for row in table.findall('w:tr',NS):
        row.remove(row.findall('w:tc',NS)[1])  # No gap between the two columns.
        row.find('w:trPr/w:trHeight',NS).set('{'+W+'}val','3118')
        for cell in row.findall('w:tc',NS):
            cell.find('w:tcPr/w:tcW',NS).set('{'+W+'}w','4819')
    prototypes = [deepcopy(row) for row in table.findall('w:tr',NS)]
    for row in table.findall('w:tr',NS): table.remove(row)
    for start in range(0,len(people),10):
        batch = people[start:start+10]
        for back in (False, True):
            for row_index in range(5):
                row = deepcopy(prototypes[row_index + (5 if back else 0)])
                for col,cell in enumerate(row.findall('w:tc',NS)):
                    index = row_index*2 + ((1-col) if back and mirror_backs else col)
                    if index >= len(batch):
                        for child in list(cell):
                            if child.tag != '{'+W+'}tcPr':cell.remove(child)
                        E.SubElement(cell,'{'+W+'}p')
                        continue
                    token = batch[index]; person = roster[token]
                    if back:
                        for paragraph in cell.findall('w:p',NS):
                            texts = paragraph.findall('.//w:t',NS)
                            label = ''.join(t.text or '' for t in texts)
                            if label.startswith('ID'):
                                texts[-1].text = ': ' + person['id']
                            elif label.startswith('Password'):
                                run=E.SubElement(paragraph,'{'+W+'}r')
                                properties=E.SubElement(run,'{'+W+'}rPr')
                                E.SubElement(properties,'{'+W+'}sz').set('{'+W+'}val','20')
                                E.SubElement(run,'{'+W+'}br')
                                E.SubElement(run,'{'+W+'}t').text=person['code']
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
                        values={'Vorname':first,'Nachname':last,'Institution':person.get('affiliation','')}
                        for text in cell.findall('.//w:t',NS):
                            if text.text in values:text.text=values[text.text]
                        image_name=f'badge-qr-{start+index}.png';rid=f'rIdBadge{start+index}'
                        parts['word/media/'+image_name]=qr_encoder(base_url.rstrip('/')+'/?badge='+token)
                        E.SubElement(relationships,'{'+REL+'}Relationship',Id=rid,Type=R+'/image',Target='media/'+image_name)
                        for blip in cell.findall('.//a:blip',NS):
                            if blip.get('{'+R+'}embed')=='rId4':blip.set('{'+R+'}embed',rid)
                    # Print calibration: translate contents 5 mm, not the sticker grid.
                    for paragraph in cell.findall('w:p',NS):
                        if paragraph.findall('.//w:t',NS):
                            props=paragraph.find('w:pPr',NS)
                            if props is None:props=E.SubElement(paragraph,'{'+W+'}pPr')
                            indent=props.find('w:ind',NS)
                            if indent is None:indent=E.SubElement(props,'{'+W+'}ind')
                            indent.set('{'+W+'}left',str(int(indent.get('{'+W+'}left','0'))+283))
                    for offset in cell.findall('.//wp:positionH/wp:posOffset',NS):
                        offset.text=str(int(offset.text)+180000)
                table.append(row)
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
