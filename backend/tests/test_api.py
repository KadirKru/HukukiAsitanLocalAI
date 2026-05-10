"""
API Endpoint Testleri
FastAPI TestClient ile gerçek endpoint'leri test eder.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        with patch("app.db.vector_store.VectorStore.get_collection_stats",
                   return_value={"kanunlar": 10, "yargitay_kararlari": 6}):
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "llm_provider" in data

    def test_root_returns_metadata(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "docs" in data


class TestQueryEndpoint:
    def _make_mock_response(self):
        from app.models.schemas import QueryResponse, QueryType, SourceDocument
        return QueryResponse(
            answer="Test cevabı",
            sources=[
                SourceDocument(
                    document_id="test_1",
                    source_type="kanun",
                    title="Türk Ceza Kanunu",
                    content="Madde 141: Hırsızlık...",
                    article_number="141",
                    metadata={},
                    relevance_score=0.92
                )
            ],
            query_type=QueryType.GENERAL,
            model_used="gpt-4o-mini",
            processing_time_ms=150.0,
            confidence_level="high"
        )

    def test_query_valid_request(self):
        with patch("app.core.rag_pipeline.RAGPipeline.run",
                   return_value=self._make_mock_response()):
            response = client.post("/query", json={
                "question": "Hırsızlık suçunun cezası nedir?",
                "query_type": "general",
                "top_k": 5
            })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) > 0

    def test_query_too_short_question(self):
        response = client.post("/query", json={"question": "??", "query_type": "general"})
        assert response.status_code == 422  # Validation error

    def test_query_missing_question(self):
        response = client.post("/query", json={"query_type": "general"})
        assert response.status_code == 422

    def test_query_law_search_type(self):
        with patch("app.core.rag_pipeline.RAGPipeline.run",
                   return_value=self._make_mock_response()):
            response = client.post("/query", json={
                "question": "İş sözleşmesi feshi bildirim süreleri nedir?",
                "query_type": "law_search"
            })
        assert response.status_code == 200


class TestDocumentEndpoints:
    def test_stats_endpoint(self):
        with patch("app.db.vector_store.VectorStore.get_collection_stats",
                   return_value={"kanunlar": 20, "yargitay_kararlari": 12}):
            response = client.get("/documents/stats")
        assert response.status_code == 200
        data = response.json()
        assert "collections" in data
        assert "total_documents" in data

    def test_upload_non_pdf_rejected(self):
        response = client.post(
            "/documents/upload-pdf",
            files={"file": ("test.txt", b"this is not a pdf", "text/plain")}
        )
        assert response.status_code == 400

    def test_upload_empty_file_rejected(self):
        response = client.post(
            "/documents/upload-pdf",
            files={"file": ("test.pdf", b"", "application/pdf")}
        )
        assert response.status_code == 400
