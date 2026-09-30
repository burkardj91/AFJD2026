import unittest
from io import BytesIO
from zipfile import ZipFile
from lxml import etree as E
from quest_badges import badge_docx, TEMPLATE, NS
from quest_registration import mock_eventfrog_xlsx, read_eventfrog
from quest_core import Quest

class BadgeTemplateTests(unittest.TestCase):
    def test_import_duplex_mapping_and_template_fidelity(self):
        rows=read_eventfrog(mock_eventfrog_xlsx());q=Quest()
        ids=q.import_registrations('ADMIN-01',rows)
        self.assertEqual(len(ids),12)
        self.assertEqual(q.registrations[ids[1]]['affiliation'],'Coop')
        self.assertEqual(q.registrations[ids[1]]['first_name'],'Alex')
        self.assertEqual(q.registrations[ids[1]]['last_name'],'Keller')
        archive=ZipFile(BytesIO(badge_docx(q.registrations,ids,'https://afjd2026.streamlit.app')))
        xml=E.fromstring(archive.read('word/document.xml'));trs=xml.findall('.//w:tr',NS)
        self.assertEqual(len(trs),20)
        self.assertEqual(len(xml.findall('.//w:drawing',NS)),12)
        self.assertFalse(xml.xpath('.//a:blip[@r:embed="rId5"]', namespaces={**NS,'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}))
        def texts(row,col):return ''.join(trs[row].findall('w:tc',NS)[col].xpath('.//w:t/text()',namespaces=NS))
        self.assertIn('Lea',texts(0,0));self.assertIn('Alex',texts(0,2))
        self.assertIn(q.registrations[ids[1]]['code'],texts(5,0))
        self.assertIn(q.registrations[ids[0]]['code'],texts(5,2))
        self.assertEqual(texts(11,0),'');self.assertEqual(texts(16,0),'')
        for row in trs[:5]:
            self.assertFalse(any(q.registrations[p]['code'] in ''.join(row.xpath('.//w:t/text()',namespaces=NS)) for p in ids))
        with ZipFile(TEMPLATE) as source:
            for name in source.namelist():
                if name not in {'word/document.xml','word/_rels/document.xml.rels'}:
                    self.assertEqual(source.read(name),archive.read(name),name)
        import cv2,numpy as np
        detector=cv2.QRCodeDetector()
        for i,person in enumerate(ids):
            image=cv2.imdecode(np.frombuffer(archive.read(f'word/media/badge-qr-{i}.png'),np.uint8),cv2.IMREAD_COLOR)
            value,_,_=detector.detectAndDecode(image)
            self.assertEqual(value,'https://afjd2026.streamlit.app/?badge='+person)
        same=ZipFile(BytesIO(badge_docx(q.registrations,ids[:1],'https://afjd2026.streamlit.app',False)))
        tree=E.fromstring(same.read('word/document.xml'))
        back=tree.findall('.//w:tr',NS)[5]
        self.assertIn(q.registrations[ids[0]]['code'],''.join(back.findall('w:tc',NS)[0].xpath('.//w:t/text()',namespaces=NS)))

if __name__=='__main__': unittest.main()
