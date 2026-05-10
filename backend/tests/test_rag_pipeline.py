"""
RAG Pipeline Testleri
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from app.models.schemas import QueryRequest, QueryType, SourceDocument


class TestRAGPipeline:
    @pytest.fixture
    def mock_sources(self):
        return [
            SourceDocument(
                document_id="kanun_5237_m141",
                source_type="kanun",
                title="Türk Ceza Kanunu",
                content="Madde 141 – Hırsızlık: Bir yıldan üç yıla kadar hapis...",
                article_number="141",
                metadata={"kanun_no": "5237"},
                relevance_score=0.91
            ),
            SourceDocument(
                document_id="yargitay_2023_1234",
                source_type="yargitay_karari",
                title="Yargıtay 12. Ceza Dairesi - 2023/5566",
                content="Sanık işyerinden mal çalmakla itham edilmiştir...",
                article_number=None,
                metadata={"daire": "12. Ceza Dairesi"},
                relevance_score=0.87
            )
        ]

    def test_pipeline_returns_response(self, mock_sources):
        with patch("app.core.retriever.LegalRetriever.retrieve", return_value=mock_sources), \
             patch("app.core.retriever.LegalRetriever.build_context_string", return_value="test context"), \
             patch("app.core.llm_client.LLMClient.generate_answer", return_value="TCK 141'e göre ceza 1-3 yıldır."), \
             patch("app.core.llm_client.LLMClient.estimate_confidence", return_value="high"):

            from app.core.rag_pipeline import RAGPipeline
            pipeline = RAGPipeline()
            request = QueryRequest(
                question="Hırsızlık suçunun cezası nedir?",
                query_type=QueryType.GENERAL,
                top_k=5
            )
            response = pipeline.run(request)

        assert response.answer is not None
        assert len(response.sources) == 2
        assert response.confidence_level == "high"
        assert response.processing_time_ms > 0

    def test_pipeline_empty_sources(self):
        with patch("app.core.retriever.LegalRetriever.retrieve", return_value=[]):
            from app.core.rag_pipeline import RAGPipeline
            pipeline = RAGPipeline()
            request = QueryRequest(
                question="Çok özel bir konu hakkında soru?",
                query_type=QueryType.GENERAL
            )
            response = pipeline.run(request)

        assert "bulunamadı" in response.answer.lower() or response.answer is not None
        assert len(response.sources) == 0

    def test_search_flags_by_type(self):
        from app.core.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()

        flags = pipeline._get_search_flags(QueryType.LAW_SEARCH)
        assert flags["search_kanunlar"] is True
        assert flags["search_yargitay"] is False

        flags = pipeline._get_search_flags(QueryType.PRECEDENT_SEARCH)
        assert flags["search_kanunlar"] is False
        assert flags["search_yargitay"] is True

        flags = pipeline._get_search_flags(QueryType.GENERAL)
        assert flags["search_kanunlar"] is True
        assert flags["search_yargitay"] is True


class TestRetriever:
    def test_build_context_string_kanun(self):
        from app.core.retriever import LegalRetriever
        r = LegalRetriever.__new__(LegalRetriever)
        sources = [
            SourceDocument(
                document_id="k1", source_type="kanun",
                title="Türk Ceza Kanunu", content="Madde 141",
                article_number="141", metadata={}, relevance_score=0.9
            )
        ]
        ctx = r.build_context_string(sources)
        assert "KANUN" in ctx
        assert "Madde 141" in ctx

    def test_build_context_string_empty(self):
        from app.core.retriever import LegalRetriever
        r = LegalRetriever.__new__(LegalRetriever)
        ctx = r.build_context_string([])
        assert "bulunamadı" in ctx.lower()


class TestTextChunker:
    def test_chunk_kanun_by_articles(self):
        from app.services.text_chunker import LegalTextChunker
        chunker = LegalTextChunker()
        text = """
        Madde 141 - Hırsızlık suçu için bir yıldan üç yıla kadar hapis cezası verilir.
        Madde 142 - Nitelikli hırsızlık suçu için üç yıldan yedi yıla kadar hapis cezası verilir.
        """
        chunks = chunker.chunk_kanun(text, "Test Kanunu", "9999")
        assert len(chunks) >= 1
        for c in chunks:
            assert len(c.text) > 0
            assert c.chunk_id.startswith("kanun_9999")

    def test_chunk_yargitay_short(self):
        from app.services.text_chunker import LegalTextChunker
        chunker = LegalTextChunker()
        text = "Davacı işçi tazminat talebinde bulunmuştur. Kabul edilmiştir."
        chunks = chunker.chunk_yargitay_karar(
            text, "Yargıtay 9. HD", "2023/100", "2023/200", "2023-01-01", "İşçi tazminat"
        )
        assert len(chunks) == 1
        assert chunks[0].metadata["daire"] == "Yargıtay 9. HD"
