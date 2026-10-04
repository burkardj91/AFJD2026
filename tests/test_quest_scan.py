import unittest,base64
from io import BytesIO
from quest_core import Quest,parse_payload
from quest_scan import decode_photo
from quest_badges import qr_image
class ScanInputTests(unittest.TestCase):
    def test_imported_id_and_link_resolve_same_person_without_private_code(self):
        q=Quest();p=q.import_registrations('ADMIN-01',[{'name':'Test Person','email':'test@example.test','source_id':'ticket:scan'}])[0]
        r=q.roster()[p]
        self.assertEqual(parse_payload(' '+r['id'].lower()+' ',q.roster()),('person',p))
        self.assertEqual(parse_payload('https://afjd2026.streamlit.app/?badge='+p,q.roster()),('person',p))
        with self.assertRaises(ValueError):parse_payload(r['code'],q.roster())
        with self.assertRaises(ValueError):parse_payload('AFJD-999999',q.roster())
        q.demo_login('AFJD-LM-264');q.scan('p-8hd2v7',r['id'])
        self.assertIn(p,q.people('p-8hd2v7'))
    def test_camera_photo_decodes_branded_badge(self):
        from PIL import Image
        value='https://afjd2026.streamlit.app/?badge=p-8hd2v7'
        im=Image.open(BytesIO(qr_image(value))).convert('RGB')
        buf=BytesIO();im.save(buf,format='JPEG',quality=94)
        self.assertEqual(decode_photo('data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()),value)
        with self.assertRaises(ValueError):decode_photo('data:image/jpeg;base64,broken')
