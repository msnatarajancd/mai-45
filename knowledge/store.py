"""Local admin-owned artifacts, not a runtime database or user-write endpoint."""
import hashlib
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from .models import SourceBundle, SourceManifest
from .sources import CURATED_SOURCES


class StoreBusyError(ValueError):
    pass


def replace_record(record, **updates):
    return type(record).model_validate({**record.model_dump(), **updates})


def context_hash(bundle: SourceBundle) -> str:
    source = bundle.source.model_dump(mode='json', exclude={'review_status', 'reviewer', 'reviewed_at'})
    chunks = [c.model_dump(mode='json', exclude={'review_status'}) for c in bundle.chunks]
    return hashlib.sha256(json.dumps({'source': source, 'chunks': chunks},
                                    sort_keys=True, ensure_ascii=True).encode()).hexdigest()


class SourceStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    @staticmethod
    def _id(source_id):
        if not isinstance(source_id, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', source_id):
            raise ValueError('invalid source ID')
        return source_id

    @contextmanager
    def admin_lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / 'admin.lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise StoreBusyError('another admin operation holds the store lock') from None
        try:
            os.close(fd)
            yield
        finally:
            lock.unlink()

    @staticmethod
    def _atomic_write(path: Path, data: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
        try:
            temporary.write_bytes(data)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def initialize(self):
        with self.admin_lock():
            manifest_path = self.root / 'source_manifest.json'
            if not manifest_path.exists():
                manifest = SourceManifest(sources=[s.source for s in CURATED_SOURCES])
                self._atomic_write(manifest_path, manifest.model_dump_json(indent=2).encode())
            else:
                SourceManifest.model_validate_json(manifest_path.read_bytes())

    def load(self, source_id: str) -> SourceBundle | None:
        path = self.root / 'records' / (self._id(source_id) + '.json')
        return SourceBundle.model_validate_json(path.read_bytes()) if path.exists() else None

    def original(self, content_hash: str) -> bytes:
        if not re.fullmatch(r'[a-f0-9]{64}', content_hash):
            raise ValueError('invalid content hash')
        return (self.root / 'originals' / (content_hash + '.bin')).read_bytes()

    def write_original(self, data: bytes) -> str:
        digest = hashlib.sha256(data).hexdigest()
        path = self.root / 'originals' / (digest + '.bin')
        if path.exists():
            if path.read_bytes() != data:
                raise ValueError('stored original content failed integrity verification')
        else:
            self._atomic_write(path, data)
        return digest

    def save_locked(self, bundle: SourceBundle):
        """Admin lock must cover read/check/write. Bundle is authoritative for export.

        Immutable snapshots retain prior provenance. Manifest is a summary; an I/O
        failure between writes may require rebuilding it from records, never grants
        publication permission. Only this module's admin operations should write it.
        """
        bundle = SourceBundle.model_validate_json(bundle.model_dump_json())
        data = bundle.model_dump_json(indent=2).encode()
        name = self._id(bundle.source.source_id)
        self._atomic_write(self.root / 'history' / name / (uuid4().hex + '.json'), data)
        self._atomic_write(self.root / 'records' / (name + '.json'), data)
        manifest_path = self.root / 'source_manifest.json'
        existing = (SourceManifest.model_validate_json(manifest_path.read_bytes()).sources
                    if manifest_path.exists() else [spec.source for spec in CURATED_SOURCES])
        sources = [bundle.source if s.source_id == name else s for s in existing]
        if name not in {s.source_id for s in sources}:
            sources.append(bundle.source)
        self._atomic_write(manifest_path, SourceManifest(sources=sources).model_dump_json(indent=2).encode())

    def load_candidate(self, source_id: str, chunk_id: str):
        from .models import ReviewCandidate
        path = self.root / 'candidates' / self._id(source_id) / (self._id(chunk_id) + '.json')
        return ReviewCandidate.model_validate_json(path.read_bytes()) if path.exists() else None

    def save_candidate_locked(self, candidate):
        from .models import ReviewCandidate
        candidate = ReviewCandidate.model_validate_json(candidate.model_dump_json())
        source_id, chunk_id = self._id(candidate.source_id), self._id(candidate.chunk_id)
        data = candidate.model_dump_json(indent=2).encode()
        self._atomic_write(self.root / 'candidate_history' / source_id / chunk_id / (uuid4().hex + '.json'), data)
        self._atomic_write(self.root / 'candidates' / source_id / (chunk_id + '.json'), data)
