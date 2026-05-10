using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
using LegalAdvisorWPF.Services;

namespace LegalAdvisorWPF;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        BuildThemePresets();
    }

    // Tema paneli aç/kapat
    private void ThemeBtn_Click(object sender, RoutedEventArgs e)
    {
        ThemePanel.Visibility = ThemePanel.Visibility == Visibility.Visible
            ? Visibility.Collapsed
            : Visibility.Visible;
    }

    // Hazır tema butonları oluştur
    private void BuildThemePresets()
    {
        var res = System.Windows.Application.Current.Resources;

        foreach (var (name, colors) in ThemeService.Presets)
        {
            var btn = new Button
            {
                Margin          = new Thickness(3),
                Padding         = new Thickness(10, 6, 10, 6),
                FontSize        = 11,
                Cursor          = System.Windows.Input.Cursors.Hand,
                Background      = (Brush)res["CardBrush"],
                Foreground      = (Brush)res["TextPrimaryBrush"],
                BorderBrush     = (Brush)res["BorderBrush"],
                BorderThickness = new Thickness(1),
            };

            var panel = new StackPanel { Orientation = Orientation.Horizontal };
            var swatch = new Ellipse
            {
                Width  = 10,
                Height = 10,
                Margin = new Thickness(0, 0, 6, 0),
                Fill   = new SolidColorBrush((Color)ColorConverter.ConvertFromString(colors.Accent))
            };
            panel.Children.Add(swatch);
            panel.Children.Add(new TextBlock { Text = name, VerticalAlignment = VerticalAlignment.Center });
            btn.Content = panel;

            var captured = colors;
            btn.Click += (_, _) =>
            {
                ThemeService.Apply(captured);
                UpdateSwatches();
            };
            ThemePresetPanel.Children.Add(btn);
        }
    }

    // Özel renk seçici: Arka Plan
    private void BgColorSwatch_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        var hex = PickColor(Application.Current.Resources["BackgroundBrush"] is SolidColorBrush sb ? $"#{sb.Color.R:X2}{sb.Color.G:X2}{sb.Color.B:X2}" : "#0F0F1A");
        if (hex == null) return;
        var c = (Color)ColorConverter.ConvertFromString(hex);
        var res = System.Windows.Application.Current.Resources;
        res["BackgroundBrush"] = new SolidColorBrush(c);
        UpdateSwatches();
    }

    // Özel renk seçici: Pencere (Card/Surface) Rengi
    private void SurfaceColorSwatch_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        var hex = PickColor(Application.Current.Resources["CardBrush"] is SolidColorBrush cb ? $"#{cb.Color.R:X2}{cb.Color.G:X2}{cb.Color.B:X2}" : "#1E1E3A");
        if (hex == null) return;
        var c = (Color)ColorConverter.ConvertFromString(hex);
        var res = System.Windows.Application.Current.Resources;
        res["CardBrush"] = new SolidColorBrush(c);
        res["SurfaceElevatedBrush"] = new SolidColorBrush(c);
        
        // SurfaceBrush biraz daha koyu, BorderBrush biraz daha açık olsun
        res["SurfaceBrush"] = new SolidColorBrush(Color.FromRgb((byte)Math.Max(c.R - 5, 0), (byte)Math.Max(c.G - 5, 0), (byte)Math.Max(c.B - 5, 0)));
        res["BorderBrush"]  = new SolidColorBrush(Color.FromRgb((byte)Math.Min(c.R + 25, 255), (byte)Math.Min(c.G + 25, 255), (byte)Math.Min(c.B + 25, 255)));
        
        UpdateSwatches();
    }

    // Özel renk seçici: Vurgu
    private void AccentColorSwatch_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        var hex = PickColor("#6C63FF");
        if (hex == null) return;
        var c = (Color)ColorConverter.ConvertFromString(hex);
        var res = System.Windows.Application.Current.Resources;

        res["AccentBrush"] = new SolidColorBrush(c);
        var secColor = Color.FromRgb(
            (byte)Math.Min(c.R + 30, 255),
            c.G,
            (byte)Math.Min(c.B + 30, 255));
        res["AccentSecondaryBrush"] = new SolidColorBrush(secColor);

        var grad = new LinearGradientBrush { StartPoint = new Point(0, 0), EndPoint = new Point(1, 0) };
        grad.GradientStops.Add(new GradientStop(c, 0));
        grad.GradientStops.Add(new GradientStop(secColor, 1));
        res["AccentGradient"] = grad;

        UpdateSwatches();
    }

    // Özel renk seçici: Yazı Rengi
    private void TextColorSwatch_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        var res = System.Windows.Application.Current.Resources;
        var hex = PickColor(res["TextPrimaryBrush"] is SolidColorBrush tb ? $"#{tb.Color.R:X2}{tb.Color.G:X2}{tb.Color.B:X2}" : "#F0F0FF");
        if (hex == null) return;
        var c = (Color)ColorConverter.ConvertFromString(hex);
        
        res["TextPrimaryBrush"] = new SolidColorBrush(c);
        
        // Secondary ve Muted renkleri Arka Plan ile karıştırarak hesapla
        Color bg = res["BackgroundBrush"] is SolidColorBrush bgBrush ? bgBrush.Color : Color.FromRgb(15, 15, 26);
        
        res["TextSecondaryBrush"] = new SolidColorBrush(Mix(c, bg, 0.70));
        res["TextMutedBrush"]     = new SolidColorBrush(Mix(c, bg, 0.45));
        
        UpdateSwatches();
    }

    // İki rengi belli bir oranda karıştırır (Text ve Arka Plan uyumu için)
    private static Color Mix(Color c1, Color c2, double ratio)
    {
        return Color.FromRgb(
            (byte)(c1.R * ratio + c2.R * (1 - ratio)),
            (byte)(c1.G * ratio + c2.G * (1 - ratio)),
            (byte)(c1.B * ratio + c2.B * (1 - ratio))
        );
    }

    // Özel renk seçici: Buton Arka Plan Rengi
    private void ButtonBgColorSwatch_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        var res = System.Windows.Application.Current.Resources;
        var hex = PickColor(res["ButtonBrush"] is SolidColorBrush bb ? $"#{bb.Color.R:X2}{bb.Color.G:X2}{bb.Color.B:X2}" : "#6C63FF");
        if (hex == null) return;
        var c = (Color)ColorConverter.ConvertFromString(hex);
        res["ButtonBrush"] = new SolidColorBrush(c);
        UpdateSwatches();
    }

    // Özel renk seçici: Buton Yazı Rengi
    private void ButtonTextColorSwatch_Click(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        var res = System.Windows.Application.Current.Resources;
        var hex = PickColor(res["ButtonTextBrush"] is SolidColorBrush bb ? $"#{bb.Color.R:X2}{bb.Color.G:X2}{bb.Color.B:X2}" : "#FFFFFF");
        if (hex == null) return;
        var c = (Color)ColorConverter.ConvertFromString(hex);
        res["ButtonTextBrush"] = new SolidColorBrush(c);
        UpdateSwatches();
    }

    // Swatch önizlemelerini güncelle
    private void UpdateSwatches()
    {
        var res = System.Windows.Application.Current.Resources;
        if (res["BackgroundBrush"] is SolidColorBrush bg)
            BgColorSwatch.Background = new SolidColorBrush(bg.Color);
        if (res["AccentBrush"] is SolidColorBrush ac)
            AccentColorSwatch.Background = new SolidColorBrush(ac.Color);
        if (res["CardBrush"] is SolidColorBrush cb)
            SurfaceColorSwatch.Background = new SolidColorBrush(cb.Color);
        if (res["TextPrimaryBrush"] is SolidColorBrush tb)
            TextColorSwatch.Background = new SolidColorBrush(tb.Color);
        if (res["ButtonBrush"] is SolidColorBrush bb)
            ButtonBgColorSwatch.Background = new SolidColorBrush(bb.Color);
        if (res["ButtonTextBrush"] is SolidColorBrush btb)
            ButtonTextColorSwatch.Background = new SolidColorBrush(btb.Color);
    }

    // Görsel renk paleti dialogu
    private string? PickColor(string defaultHex)
    {
        var dlg = new LegalAdvisorWPF.Views.ColorPickerWindow(defaultHex)
        {
            Owner = this
        };
        return dlg.ShowDialog() == true ? dlg.SelectedHex : null;
    }
}

