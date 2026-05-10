using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using LegalAdvisorWPF.Models;

namespace LegalAdvisorWPF.Services;

// api ile baglanti yapan sinif
public class ApiService
{
    private readonly HttpClient _http;
    private readonly JsonSerializerOptions _jsonOptions;
    private string _baseUrl;

    public ApiService(string baseUrl = "http://localhost:8000")
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _http = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(120)
        };
        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };
    }

    // baglanti guncelleme
    public void SetBaseUrl(string url) => _baseUrl = url.TrimEnd('/');

    // sunucu kontrolu
    public async Task<(bool IsOnline, string Status)> CheckHealthAsync()
    {
        try
        {
            var response = await _http.GetAsync($"{_baseUrl}/health");
            if (!response.IsSuccessStatusCode)
                return (false, $"HTTP {(int)response.StatusCode}");

            var json = await response.Content.ReadAsStringAsync();
            var health = JsonSerializer.Deserialize<HealthResponse>(json, _jsonOptions);
            return (health?.Status == "ok", health?.VectorDbStatus ?? "Bilinmiyor");
        }
        catch (Exception ex)
        {
            return (false, $"Bağlantı hatası: {ex.Message}");
        }
    }

    // yapay zekaya soruyu yolla
    public async Task<QueryResponse> QueryAsync(QueryRequest request)
    {
        var json = JsonSerializer.Serialize(request);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        HttpResponseMessage response;
        try
        {
            response = await _http.PostAsync($"{_baseUrl}/query", content);
        }
        catch (TaskCanceledException)
        {
            throw new TimeoutException("API yanıt vermedi (zaman aşımı). Sunucuyu kontrol edin.");
        }
        catch (HttpRequestException ex)
        {
            throw new Exception($"Sunucuya bağlanılamadı: {ex.Message}");
        }

        var responseJson = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
        {
            var error = TryExtractDetail(responseJson);
            throw new Exception($"API hatası ({(int)response.StatusCode}): {error}");
        }

        return JsonSerializer.Deserialize<QueryResponse>(responseJson, _jsonOptions)
               ?? throw new Exception("Geçersiz API cevabı.");
    }

    // dosya isleri
    public async Task<UploadPdfResponse> UploadPdfAsync(string filePath)
    {
        var fileBytes = await File.ReadAllBytesAsync(filePath);
        var fileName = Path.GetFileName(filePath);

        using var form = new MultipartFormDataContent();
        var fileContent = new ByteArrayContent(fileBytes);
        fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/pdf");
        form.Add(fileContent, "file", fileName);

        HttpResponseMessage response;
        try
        {
            response = await _http.PostAsync($"{_baseUrl}/documents/upload-pdf", form);
        }
        catch (Exception ex)
        {
            throw new Exception($"PDF yükleme başarısız: {ex.Message}");
        }

        var responseJson = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
        {
            var error = TryExtractDetail(responseJson);
            throw new Exception($"PDF yükleme hatası: {error}");
        }

        return JsonSerializer.Deserialize<UploadPdfResponse>(responseJson, _jsonOptions)
               ?? throw new Exception("Geçersiz yükleme cevabı.");
    }

    // pdf okutma
    public async Task<AnalyzePdfResponse> AnalyzePdfAsync(string filePath, string analysisType = "general", string llmProvider = "gemini")
    {
        var fileBytes = await File.ReadAllBytesAsync(filePath);
        var fileName = Path.GetFileName(filePath);

        using var form = new MultipartFormDataContent();
        var fileContent = new ByteArrayContent(fileBytes);
        fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/pdf");
        form.Add(fileContent, "file", fileName);

        var response = await _http.PostAsync(
            $"{_baseUrl}/documents/analyze-pdf?analysis_type={analysisType}&llm_provider={llmProvider}", form);

        var responseJson = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
            throw new Exception($"PDF analiz hatası: {TryExtractDetail(responseJson)}");

        return JsonSerializer.Deserialize<AnalyzePdfResponse>(responseJson, _jsonOptions)
               ?? throw new Exception("Geçersiz analiz cevabı.");
    }

    // istatistikleri cek
    public async Task<Dictionary<string, object>> GetStatsAsync()
    {
        var response = await _http.GetAsync($"{_baseUrl}/documents/stats");
        var json = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<Dictionary<string, object>>(json, _jsonOptions) ?? new();
    }


    private static string TryExtractDetail(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            if (doc.RootElement.TryGetProperty("detail", out var detail))
                return detail.GetString() ?? json;
        }
        catch { }
        return json.Length > 200 ? json[..200] : json;
    }
}
