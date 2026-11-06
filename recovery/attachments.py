"""Bounded JPEG/PNG decoding. Originals are preserved; previews are derivatives."""
import hashlib
import io
import re
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from .insurance_models import InsuranceAttachment, SavedPhoto, EvidenceType

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_CASE_BYTES = 50 * 1024 * 1024
MAX_ATTACHMENTS = 20
MAX_PIXELS = 12_000_000


def validate_photo(content, filename, *, case_id, damage_id=None,
                   evidence_type=EvidenceType.PHOTOGRAPH, description=''):
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_PHOTO_BYTES:
        raise ValueError('Photographs must be between 1 byte and 5 MiB.')
    if (not isinstance(filename, str) or len(filename) > 200
            or not re.fullmatch(r'[^/\\:\x00-\x1f\x7f]+\.(?:jpg|jpeg|png)', filename, re.I)
            or filename.startswith('.') or '..' in filename):
        raise ValueError('Use a simple JPEG/PNG filename without paths or unsafe characters.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                format = image.format
                width, height = image.size
                if format not in {'JPEG', 'PNG'} or getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Only non-animated JPEG and PNG photographs are accepted.')
                if width * height > MAX_PIXELS or max(width, height) > 10000:
                    raise ValueError('Image dimensions exceed the 12-megapixel / 10000-pixel limit.')
                if (format == 'PNG') != filename.lower().endswith('.png'):
                    raise ValueError('Filename extension does not match the actual image content.')
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise ValueError('The image is corrupt, unsupported or too large to decode.') from error
    metadata = InsuranceAttachment(case_id=case_id, damage_id=damage_id,
        evidence_type=evidence_type, original_name=filename,
        media_type='image/png' if format == 'PNG' else 'image/jpeg',
        sha256=hashlib.sha256(content).hexdigest(), byte_count=len(content),
        width=width, height=height, description=description)
    return SavedPhoto(metadata=metadata, content=content)


def verify_saved_photo(photo):
    meta = photo.metadata
    checked = validate_photo(photo.content, meta.original_name, case_id=meta.case_id,
        damage_id=meta.damage_id, evidence_type=meta.evidence_type, description=meta.description)
    for name in ('media_type', 'sha256', 'byte_count', 'width', 'height'):
        if getattr(meta, name) != getattr(checked.metadata, name):
            raise ValueError('Saved attachment content/hash does not match its metadata.')


def thumbnail(photo):
    verify_saved_photo(photo)
    with Image.open(io.BytesIO(photo.content)) as image:
        preview = ImageOps.exif_transpose(image).convert('RGB')
        preview.thumbnail((640, 480))
        output = io.BytesIO()
        preview.save(output, 'JPEG')
        return output.getvalue()
