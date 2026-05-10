using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace LegalAdvisorWPF.Converters;

/// <summary>bool → Visibility dönüştürücü</summary>
public class BoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => value is true ? Visibility.Visible : Visibility.Collapsed;

    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => value is Visibility.Visible;
}

/// <summary>bool → Visibility (ters)</summary>
public class InverseBoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => value is true ? Visibility.Collapsed : Visibility.Visible;

    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => value is not Visibility.Visible;
}

/// <summary>Güven seviyesi string → Renk dönüştürücü</summary>
public class ConfidenceToColorConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => value?.ToString() switch
        {
            "high" => new SolidColorBrush(Color.FromRgb(34, 197, 94)),   // yeşil
            "medium" => new SolidColorBrush(Color.FromRgb(234, 179, 8)), // sarı
            _ => new SolidColorBrush(Color.FromRgb(239, 68, 68))         // kırmızı
        };

    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => throw new NotImplementedException();
}

/// <summary>Kaynak türü string → arkaplan rengi</summary>
public class SourceTypeToBrushConverter : IValueConverter
{
    private static readonly SolidColorBrush KanunBrush = new(Color.FromArgb(60, 59, 130, 246));
    private static readonly SolidColorBrush YargitayBrush = new(Color.FromArgb(60, 168, 85, 247));

    public object Convert(object value, Type t, object p, CultureInfo c)
        => value?.ToString() == "kanun" ? KanunBrush : YargitayBrush;

    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => throw new NotImplementedException();
}

/// <summary>double skoru yüzde string'e çevirir</summary>
public class ScoreToPercentConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => value is double d ? $"%{d * 100:F0}" : "–";

    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => throw new NotImplementedException();
}

/// <summary>Boş string → Visibility (boşsa Collapsed)</summary>
public class StringToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type t, object p, CultureInfo c)
        => string.IsNullOrEmpty(value?.ToString()) ? Visibility.Collapsed : Visibility.Visible;

    public object ConvertBack(object value, Type t, object p, CultureInfo c)
        => throw new NotImplementedException();
}
