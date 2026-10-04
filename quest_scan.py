"""Decode a transient camera photo; no images are persisted."""
import base64
from io import BytesIO
from PIL import Image, ImageOps
import zxingcpp

def decode_photo(value):
    try:
        if not isinstance(value,str) or len(value)>12_000_000 or not value.startswith('data:image/jpeg;base64,'):
            raise ValueError()
        image=Image.open(BytesIO(base64.b64decode(value.split(',',1)[1],validate=True)))
        if image.width*image.height>16_000_000: raise ValueError()
        image=ImageOps.exif_transpose(image).convert('RGB')
        codes={r.text for r in zxingcpp.read_barcodes(image) if r.format==zxingcpp.BarcodeFormat.QRCode}
    except Exception as error:
        raise ValueError('Foto nicht lesbar. Nimm ein neues Foto auf oder gib die Badge-ID ein.') from error
    if not codes: raise ValueError('Kein QR-Code erkannt. Fotografiere ihn näher, scharf und mit allen vier Rändern – oder gib die Badge-ID ein.')
    if len(codes)>1: raise ValueError('Mehrere QR-Codes erkannt. Fotografiere nur einen Badge.')
    return codes.pop()
