"""
OncoSentinel v2.0 — Object Storage Service
Satisfies: FR-01, NFR-05, NFR-14 (MinIO with local filesystem fallback)
"""
from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import Optional

from services.core.logging import get_logger
from services.core.settings import get_settings

logger = get_logger(__name__)


class ObjectStorageService:
    """Manages storage of uploaded images, PDFs, heatmaps, and generated reports."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.local_base_dir = Path("data/storage")
        self.local_base_dir.mkdir(parents=True, exist_ok=True)
        self._minio_client = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            from minio import Minio

            self._minio_client = Minio(
                self.settings.minio_endpoint,
                access_key=self.settings.minio_access_key.get_secret_value(),
                secret_key=self.settings.minio_secret_key.get_secret_value(),
                secure=self.settings.minio_secure,
            )
            # Ensure buckets exist
            for bucket in [
                self.settings.minio_bucket_images,
                self.settings.minio_bucket_artifacts,
                self.settings.minio_bucket_reports,
            ]:
                if not self._minio_client.bucket_exists(bucket):
                    self._minio_client.make_bucket(bucket)
            logger.info("minio_storage_connected", endpoint=self.settings.minio_endpoint)
        except Exception as exc:
            logger.info("minio_not_available_using_local_storage", reason=str(exc))
            self._minio_client = None

    def store_file(
        self,
        bucket_name: str,
        file_bytes: bytes,
        file_extension: str = "bin",
        object_id: Optional[str] = None,
    ) -> str:
        """
        Store file bytes into MinIO or local filesystem.
        Returns a URI identifier (e.g. s3://bucket/id.ext or file:///path/id.ext).
        """
        oid = object_id or str(uuid.uuid4())
        filename = f"{oid}.{file_extension.lstrip('.')}"

        if self._minio_client:
            try:
                data_stream = io.BytesIO(file_bytes)
                self._minio_client.put_object(
                    bucket_name,
                    filename,
                    data_stream,
                    length=len(file_bytes),
                )
                return f"s3://{bucket_name}/{filename}"
            except Exception as exc:
                logger.warning("minio_put_failed_falling_back_to_disk", error=str(exc))

        # Local fallback
        bucket_dir = self.local_base_dir / bucket_name
        bucket_dir.mkdir(parents=True, exist_ok=True)
        filepath = bucket_dir / filename
        filepath.write_bytes(file_bytes)
        return str(filepath.resolve())

    def retrieve_file(self, uri: str) -> bytes:
        """Retrieve file bytes by URI."""
        if uri.startswith("s3://") and self._minio_client:
            parts = uri.replace("s3://", "").split("/", 1)
            bucket, obj_name = parts[0], parts[1]
            response = self._minio_client.get_object(bucket, obj_name)
            return response.read()
        elif uri.startswith("file://") or os.path.exists(uri):
            clean_path = uri.replace("file:///", "").replace("file://", "")
            return Path(clean_path).read_bytes()
        else:
            # Check relative to local base dir
            local_candidate = self.local_base_dir / uri
            if local_candidate.exists():
                return local_candidate.read_bytes()
            raise FileNotFoundError(f"Object URI not found: {uri}")


_storage_singleton: Optional[ObjectStorageService] = None


def get_storage_service() -> ObjectStorageService:
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = ObjectStorageService()
    return _storage_singleton
