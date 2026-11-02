"""
OncoSentinel v2.0 — Document Parsing and OCR Service
Satisfies: FR-01, FR-02 (PDF text, page extraction, OCR)
Grounded in: Shyr et al. (2026) regarding text extraction from unstructured clinical notes
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image

from services.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentParseResult:
    text: str
    num_pages: int
    extracted_images: list[bytes] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    ocr_applied: bool = False


class DocumentParser:
    """Extracts text and embedded images from PDFs or clinical reports."""

    def parse_pdf(self, pdf_bytes: bytes) -> DocumentParseResult:
        """Parse PDF using PyMuPDF (fitz) if available, with resilient fallback."""
        text_content: list[str] = []
        extracted_images: list[bytes] = []
        num_pages = 1
        meta: dict = {}

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            num_pages = len(doc)
            meta = doc.metadata or {}

            for page_num in range(num_pages):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    text_content.append(page_text.strip())

                # Extract embedded images if any
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image.get("image")
                    if image_bytes:
                        extracted_images.append(image_bytes)

            full_text = "\n\n".join(text_content).strip()
            ocr_needed = len(full_text) < 50 and len(extracted_images) > 0

            return DocumentParseResult(
                text=full_text,
                num_pages=num_pages,
                extracted_images=extracted_images,
                metadata=meta,
                ocr_applied=ocr_needed,
            )

        except ImportError:
            logger.info("pymupdf_not_found_using_fallback_extractor")
            # Resilient plain-text / binary stream scanner for PDF strings
            extracted = self._fallback_extract_text(pdf_bytes)
            return DocumentParseResult(
                text=extracted,
                num_pages=1,
                extracted_images=[],
                metadata={"engine": "fallback_stream_parser"},
                ocr_applied=False,
            )
        except Exception as exc:
            logger.warning("pdf_parse_error", error=str(exc))
            return DocumentParseResult(
                text="",
                num_pages=0,
                extracted_images=[],
                metadata={"error": str(exc)},
                ocr_applied=False,
            )

    def ocr_image(self, image_bytes: bytes) -> str:
        """Run OCR on image bytes using pytesseract or return empty string."""
        try:
            import pytesseract

            img = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception:
            # Fallback if tesseract binary is not on host
            return ""

    def _fallback_extract_text(self, pdf_bytes: bytes) -> str:
        """Fallback byte scanner for ASCII/UTF-8 text chunks inside PDF streams."""
        text_parts = []
        try:
            # Look for readable ASCII chunks longer than 4 chars
            raw_str = pdf_bytes.decode("latin-1", errors="ignore")
            import re
            tokens = re.findall(r"\(([^\(\)]{4,})\)", raw_str)
            if tokens:
                return " ".join(tokens)
        except Exception:
            pass
        return ""
