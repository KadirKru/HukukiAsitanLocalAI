using System.Text.Json.Serialization;

namespace LegalAdvisorWPF.Models;

/// <summary>Hukuki sorgu isteği modeli</summary>
public class QueryRequest
{
    [JsonPropertyName("question")]
    public string Question { get; set; } = string.Empty;

    [JsonPropertyName("query_type")]
    public string QueryType { get; set; } = "general";

    [JsonPropertyName("top_k")]
    public int TopK { get; set; } = 5;

    [JsonPropertyName("llm_provider")]
    public string? LlmProvider { get; set; }

    [JsonPropertyName("chat_history")]
    public List<Message> ChatHistory { get; set; } = new();
}

/// <summary>Sohbet mesajı modeli</summary>
public class Message
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
}

/// <summary>AI cevabı + kaynaklar</summary>
public class QueryResponse
{
    [JsonPropertyName("answer")]
    public string Answer { get; set; } = string.Empty;

    [JsonPropertyName("sources")]
    public List<SourceDocument> Sources { get; set; } = new();

    [JsonPropertyName("query_type")]
    public string QueryType { get; set; } = string.Empty;

    [JsonPropertyName("model_used")]
    public string ModelUsed { get; set; } = string.Empty;

    [JsonPropertyName("processing_time_ms")]
    public double ProcessingTimeMs { get; set; }

    [JsonPropertyName("confidence_level")]
    public string ConfidenceLevel { get; set; } = string.Empty;
}

/// <summary>Referans gösterilen kaynak belge</summary>
public class SourceDocument
{
    [JsonPropertyName("document_id")]
    public string DocumentId { get; set; } = string.Empty;

    [JsonPropertyName("source_type")]
    public string SourceType { get; set; } = string.Empty;

    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;

    [JsonPropertyName("article_number")]
    public string? ArticleNumber { get; set; }

    [JsonPropertyName("relevance_score")]
    public double RelevanceScore { get; set; }

    [JsonPropertyName("metadata")]
    public Dictionary<string, string> Metadata { get; set; } = new();

    /// <summary>Kaynak türüne göre ikon</summary>
    public string SourceIcon => SourceType == "kanun" ? "⚖️" : "🏛️";

    /// <summary>Kaynak türü Türkçe etiketi</summary>
    public string SourceLabel => SourceType == "kanun" ? "Kanun Maddesi" : "Yargıtay Kararı";

    /// <summary>% cinsinden alaka skoru</summary>
    public string RelevancePercent => $"%{(RelevanceScore * 100):F0}";
}

/// <summary>PDF yükleme yanıtı</summary>
public class UploadPdfResponse
{
    [JsonPropertyName("file_name")]
    public string FileName { get; set; } = string.Empty;

    [JsonPropertyName("pages_processed")]
    public int PagesProcessed { get; set; }

    [JsonPropertyName("chunks_created")]
    public int ChunksCreated { get; set; }

    [JsonPropertyName("indexed")]
    public bool Indexed { get; set; }

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    [JsonPropertyName("doc_id")]
    public string DocId { get; set; } = string.Empty;
}

/// <summary>PDF analiz yanıtı</summary>
public class AnalyzePdfResponse
{
    [JsonPropertyName("file_name")]
    public string FileName { get; set; } = string.Empty;

    [JsonPropertyName("pages")]
    public int Pages { get; set; }

    [JsonPropertyName("analysis_type")]
    public string AnalysisType { get; set; } = string.Empty;

    [JsonPropertyName("analysis")]
    public string Analysis { get; set; } = string.Empty;
}

/// <summary>Sağlık kontrolü yanıtı</summary>
public class HealthResponse
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = string.Empty;

    [JsonPropertyName("version")]
    public string Version { get; set; } = string.Empty;

    [JsonPropertyName("llm_provider")]
    public string LlmProvider { get; set; } = string.Empty;

    [JsonPropertyName("vector_db_status")]
    public string VectorDbStatus { get; set; } = string.Empty;
}
