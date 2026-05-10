"""
PDF Servis Testleri
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


class TestPDFService:
    def _make_simple_pdf(self) -> bytes:
        """Basit test PDF'i oluşturur."""
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 100), "Türk Hukuku Test Belgesi\n\nMadde 1 - Bu bir test maddesidir.")
            buf = BytesIO()
            doc.save(buf)
            return buf.getvalue()
        except Exception:
            return b"%PDF-1.4 test"

    def test_clean_text(self):
        from app.services.pdf_service import PDFService
        svc = PDFService()
        dirty = "Test\n\n\n\nMetin  fazla boşluk"
        cleaned = svc._clean_text(dirty)
        assert "\n\n\n" not in cleaned
        assert "  " not in cleaned

    def test_metadata_extraction_invalid(self):
        """Geçersiz PDF için graceful hata."""
        from app.services.pdf_service import PDFService
        svc = PDFService()
        try:
            svc.get_pdf_metadata(b"not a pdf")
            assert False, "Hata bekleniyor"
        except Exception:
            pass  # Beklenen davranış

    def test_process_and_index_returns_doc_id(self):
        from app.services.pdf_service import PDFService
        pdf_bytes = self._make_simple_pdf()
        svc = PDFService()

        with patch.object(svc.embedder, 'embed_texts', return_value=[[0.1] * 384]):
            with patch('chromadb.PersistentClient') as mock_chroma:
                mock_coll = MagicMock()
                mock_chroma.return_value.get_or_create_collection.return_value = mock_coll
                result = svc.process_and_index(pdf_bytes, "test.pdf")

        assert "doc_id" in result
        assert result["doc_id"].startswith("pdf_")
