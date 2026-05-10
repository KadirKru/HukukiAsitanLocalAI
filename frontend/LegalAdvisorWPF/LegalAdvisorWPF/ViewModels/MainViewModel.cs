using System.Collections.ObjectModel;
using System.IO;
using System.Windows;
using System.Windows.Input;
using LegalAdvisorWPF.Models;
using LegalAdvisorWPF.Services;
using Microsoft.Win32;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace LegalAdvisorWPF.ViewModels;

public class MainViewModel : BaseViewModel
{
    private readonly ApiService _api;
    private readonly List<Message> _chatHistory = new();

    // tanimlamalar
    private string _question = string.Empty;
    public string Question
    {
        get => _question;
        set => SetProperty(ref _question, value);
    }

    private string _answer = string.Empty;
    public string Answer
    {
        get => _answer;
        set
        {
            SetProperty(ref _answer, value);
            OnPropertyChanged(nameof(IsAnswerEmpty));
        }
    }

    /// <summary>true when no answer yet — used for placeholder visibility</summary>
    public bool IsAnswerEmpty => string.IsNullOrEmpty(_answer);

    /// <summary>true when sources list is empty — used for placeholder visibility</summary>
    public bool IsSourcesEmpty => Sources.Count == 0;

    private bool _isLoading;
    public bool IsLoading
    {
        get => _isLoading;
        set
        {
            SetProperty(ref _isLoading, value);
            OnPropertyChanged(nameof(IsNotLoading));
        }
    }
    public bool IsNotLoading => !_isLoading;

    private string _statusMessage = "Hazır";
    public string StatusMessage
    {
        get => _statusMessage;
        set => SetProperty(ref _statusMessage, value);
    }



    private const int TopK = 7;


    private string _uploadedFileName = "Dosya seçilmedi";
    public string UploadedFileName
    {
        get => _uploadedFileName;
        set => SetProperty(ref _uploadedFileName, value);
    }

    private string _pdfAnalysis = string.Empty;
    public string PdfAnalysis
    {
        get => _pdfAnalysis;
        set => SetProperty(ref _pdfAnalysis, value);
    }

    private string _processingInfo = string.Empty;
    public string ProcessingInfo
    {
        get => _processingInfo;
        set => SetProperty(ref _processingInfo, value);
    }

    private string _confidenceBadge = string.Empty;
    public string ConfidenceBadge
    {
        get => _confidenceBadge;
        set => SetProperty(ref _confidenceBadge, value);
    }

    private bool _isApiOnline;
    public bool IsApiOnline
    {
        get => _isApiOnline;
        set => SetProperty(ref _isApiOnline, value);
    }

    private string _apiStatusText = "Kontrol ediliyor...";
    public string ApiStatusText
    {
        get => _apiStatusText;
        set => SetProperty(ref _apiStatusText, value);
    }

    private string _selectedPdfPath = string.Empty;

    // yapay zeka model listesi
    public ObservableCollection<string> AvailableProviders { get; } = new()
    {
        "Gemini API (Cloud)",
        "Ollama Llama3 (Local)"
    };

    private string _selectedProvider = "Gemini API (Cloud)";
    public string SelectedProvider
    {
        get => _selectedProvider;
        set => SetProperty(ref _selectedProvider, value);
    }

    // drafting falan
    public ObservableCollection<string> AvailableQueryTypes { get; } = new()
    {
        "Genel Danışmanlık",
        "Dilekçe / Taslak Oluşturucu"
    };

    private string _selectedQueryType = "Genel Danışmanlık";
    public string SelectedQueryType
    {
        get => _selectedQueryType;
        set => SetProperty(ref _selectedQueryType, value);
    }

    public ObservableCollection<SourceDocument> Sources { get; } = new();

    // komutlar fln
    public ICommand SendQueryCommand { get; }
    public ICommand SelectPdfCommand { get; }
    public ICommand UploadAndAnalyzePdfCommand { get; }
    public ICommand ClearAllCommand { get; }
    public ICommand CheckApiCommand { get; }
    public ICommand CopyPdfAnalysisCommand { get; }
    public ICommand ExportToPdfCommand { get; }

    // baslangic
    public MainViewModel()
    {
        QuestPDF.Settings.License = LicenseType.Community;
        _api = new ApiService();

        Sources.CollectionChanged += (_, _) => OnPropertyChanged(nameof(IsSourcesEmpty));

        SendQueryCommand = new RelayCommand(async _ => await SendQueryAsync(), _ => !IsLoading && !string.IsNullOrWhiteSpace(Question));
        SelectPdfCommand = new RelayCommand(_ => SelectPdf());
        UploadAndAnalyzePdfCommand = new RelayCommand(async _ => await UploadAndAnalyzePdfAsync(), _ => !IsLoading && !string.IsNullOrEmpty(_selectedPdfPath));
        ClearAllCommand = new RelayCommand(_ => ClearAll());
        CheckApiCommand = new RelayCommand(async _ => await CheckApiStatusAsync());
        CopyPdfAnalysisCommand = new RelayCommand(_ => CopyPdfAnalysis(), _ => !string.IsNullOrEmpty(PdfAnalysis));
        ExportToPdfCommand = new RelayCommand(_ => ExportToPdf(), _ => !string.IsNullOrEmpty(Answer));

        // İlk bağlantı kontrolü
        _ = CheckApiStatusAsync();
    }

    // asil islem yapan yer
    private async Task SendQueryAsync()
    {
        if (string.IsNullOrWhiteSpace(Question)) return;

        IsLoading = true;
        StatusMessage = "Sorgu işleniyor...";
        
        string currentQuestion = Question;
        Question = string.Empty; // Soru kutusunu hemen temizle

        try
        {
            var request = new QueryRequest
            {
                Question = currentQuestion,
                QueryType = SelectedQueryType == "Dilekçe / Taslak Oluşturucu" ? "drafting" : "general",
                TopK = TopK,
                LlmProvider = SelectedProvider.Contains("Local") ? "ollama" : "gemini",
                ChatHistory = new List<Message>(_chatHistory)
            };

            // Kullanıcının mesajını geçmişe ekle
            _chatHistory.Add(new Message { Role = "user", Content = currentQuestion });

            var response = await _api.QueryAsync(request);

            // Yapay zekanın cevabını geçmişe ekle
            _chatHistory.Add(new Message { Role = "assistant", Content = response.Answer });

            // Ekranda sohbet gibi alt alta ekle
            string separator = string.IsNullOrEmpty(Answer) ? "" : "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";
            Answer += $"{separator}SİZ:\n{currentQuestion}\n\nAI:\n{response.Answer}";
            ProcessingInfo = $"⏱ {response.ProcessingTimeMs:F0}ms  |  🤖 {response.ModelUsed}  |  📄 {response.Sources.Count} kaynak";
            ConfidenceBadge = response.ConfidenceLevel switch
            {
                "high" => "✅ Yüksek Güven",
                "medium" => "🟡 Orta Güven",
                _ => "🔴 Düşük Güven"
            };

            foreach (var src in response.Sources)
                Sources.Add(src);

            StatusMessage = $"✓ Cevap oluşturuldu — {response.Sources.Count} kaynak bulundu";
        }
        catch (Exception ex)
        {
            Answer = $"❌ Hata: {ex.Message}";
            StatusMessage = "Sorgu başarısız";
        }
        finally
        {
            IsLoading = false;
        }
    }

    private void SelectPdf()
    {
        var dialog = new OpenFileDialog
        {
            Filter = "PDF Dosyaları (*.pdf)|*.pdf",
            Title = "Hukuki PDF Belgesini Seçin"
        };

        if (dialog.ShowDialog() == true)
        {
            _selectedPdfPath = dialog.FileName;
            UploadedFileName = Path.GetFileName(dialog.FileName);
            PdfAnalysis = string.Empty;
            StatusMessage = $"Dosya seçildi: {UploadedFileName}";
        }
    }

    private async Task UploadAndAnalyzePdfAsync()
    {
        if (string.IsNullOrEmpty(_selectedPdfPath)) return;

        IsLoading = true;
        PdfAnalysis = string.Empty;
        StatusMessage = "PDF yükleniyor ve analiz ediliyor...";

        try
        {
            // PDF'i analiz et (RAG + LLM)
            var provider = SelectedProvider.Contains("Local") ? "ollama" : "gemini";
            var analyzeResponse = await _api.AnalyzePdfAsync(_selectedPdfPath, "general", provider);
            PdfAnalysis = analyzeResponse.Analysis;

            // Arka planda indexle
            _ = _api.UploadPdfAsync(_selectedPdfPath);

            StatusMessage = $"✓ PDF analizi tamamlandı — {analyzeResponse.Pages} sayfa işlendi";
        }
        catch (Exception ex)
        {
            PdfAnalysis = $"❌ PDF analiz hatası: {ex.Message}";
            StatusMessage = "PDF analizi başarısız";
        }
        finally
        {
            IsLoading = false;
        }
    }

    private void ClearAll()
    {
        Question = string.Empty;
        Answer = string.Empty;
        _chatHistory.Clear();
        PdfAnalysis = string.Empty;
        ProcessingInfo = string.Empty;
        ConfidenceBadge = string.Empty;
        Sources.Clear();
        _selectedPdfPath = string.Empty;
        UploadedFileName = "Dosya seçilmedi";
        StatusMessage = "Temizlendi";
    }

    private void CopyPdfAnalysis()
    {
        if (!string.IsNullOrEmpty(PdfAnalysis))
        {
            try
            {
                Clipboard.SetText(PdfAnalysis);
                StatusMessage = "✓ PDF analizi panoya kopyalandı";
            }
            catch
            {
                StatusMessage = "❌ Panoya kopyalanamadı";
            }
        }
    }

    private async Task CheckApiStatusAsync()
    {
        ApiStatusText = "Bağlanıyor...";
        IsApiOnline = false;

        var (online, status) = await _api.CheckHealthAsync();
        IsApiOnline = online;
        ApiStatusText = online ? $"🟢 Bağlı  |  {status}" : $"🔴 Bağlantı yok  |  {status}";
        StatusMessage = online ? "API hazır" : "API'ye bağlanılamadı — sunucuyu başlatın";
    }

    private void ExportToPdf()
    {
        // En son AI cevabını bul
        var lastAiMessage = _chatHistory.LastOrDefault(m => m.Role == "assistant")?.Content;
        if (string.IsNullOrEmpty(lastAiMessage))
        {
            StatusMessage = "❌ Dışa aktarılacak AI cevabı bulunamadı.";
            return;
        }

        var dialog = new SaveFileDialog
        {
            Filter = "PDF Dosyası (*.pdf)|*.pdf",
            Title = "Çıktıyı PDF Olarak Kaydet",
            FileName = $"Hukuki_Belge_{DateTime.Now:yyyyMMdd_HHmm}.pdf"
        };

        if (dialog.ShowDialog() == true)
        {
            try
            {
                StatusMessage = "PDF oluşturuluyor...";
                
                Document.Create(container =>
                {
                    container.Page(page =>
                    {
                        page.Size(PageSizes.A4);
                        page.Margin(2, Unit.Centimetre);
                        page.PageColor(Colors.White);
                        page.DefaultTextStyle(x => x.FontSize(11).FontFamily(Fonts.Arial));

                        page.Content().PaddingVertical(1, Unit.Centimetre).Text(text =>
                        {
                            text.Span(lastAiMessage);
                        });

                        page.Footer().AlignCenter().Text(x =>
                        {
                            x.Span("Sayfa ");
                            x.CurrentPageNumber();
                            x.Span(" / ");
                            x.TotalPages();
                        });
                    });
                })
                .GeneratePdf(dialog.FileName);

                StatusMessage = $"✓ PDF başarıyla kaydedildi: {Path.GetFileName(dialog.FileName)}";
            }
            catch (Exception ex)
            {
                StatusMessage = $"❌ PDF kaydedilemedi: {ex.Message}";
            }
        }
    }
}

// kendi halinde komut sinifi
public class RelayCommand : ICommand
{
    private readonly Action<object?> _execute;
    private readonly Func<object?, bool>? _canExecute;

    public RelayCommand(Action<object?> execute, Func<object?, bool>? canExecute = null)
    {
        _execute = execute;
        _canExecute = canExecute;
    }

    public event EventHandler? CanExecuteChanged
    {
        add => CommandManager.RequerySuggested += value;
        remove => CommandManager.RequerySuggested -= value;
    }

    public bool CanExecute(object? p) => _canExecute?.Invoke(p) ?? true;
    public void Execute(object? p) => _execute(p);
}
