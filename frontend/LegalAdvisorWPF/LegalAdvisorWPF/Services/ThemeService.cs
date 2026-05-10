using System.Windows;
using System.Windows.Media;

namespace LegalAdvisorWPF.Services
{
    /// <summary>
    /// Uygulama renk temasını çalışma zamanında değiştiren servis.
    /// App.xaml'daki SolidColorBrush kaynaklarını güncelleyerek tüm UI'ı anında yeniler.
    /// </summary>
    public static class ThemeService
    {
        // Önceden tanımlı temalar
        public static readonly (string Name, ThemeColors Colors)[] Presets = new[]
        {
            ("Gece Moru",    new ThemeColors("#0F0F1A","#1A1A2E","#16213E","#1E1E3A","#2D2D5E","#6C63FF","#A855F7")),
            ("Okyanus",      new ThemeColors("#0A1628","#0D1F3C","#0F2744","#122D52","#1A3A6B","#0EA5E9","#38BDF8")),
            ("Orman",        new ThemeColors("#0A1F0A","#0F2B0F","#122E12","#163516","#1E4A1E","#22C55E","#4ADE80")),
            ("Ember",        new ThemeColors("#1A0A00","#2B1300","#311500","#3A1A00","#5E2A00","#F97316","#FB923C")),
            ("Gül",          new ThemeColors("#1A0A14","#2B1222","#311427","#3A152C","#5E1F47","#EC4899","#F472B6")),
            ("Buz",          new ThemeColors("#0A0F1A","#111827","#131F2E","#172335","#1F2F4E","#67E8F9","#A5F3FC")),
            ("Gündüz",       new ThemeColors("#F0F4F8","#FFFFFF","#F8FAFC","#FFFFFF","#E2E8F0","#6C63FF","#A855F7")),
        };

        public static void Apply(ThemeColors t)
        {
            var res = Application.Current.Resources;
            Set(res, "BackgroundBrush",       t.Background);
            Set(res, "SurfaceBrush",          t.Surface);
            Set(res, "SurfaceElevatedBrush",  t.SurfaceElevated);
            Set(res, "CardBrush",             t.Card);
            Set(res, "BorderBrush",           t.Border);
            Set(res, "AccentBrush",           t.Accent);
            Set(res, "AccentSecondaryBrush",  t.AccentSecondary);

            // Gündüz modunda yazıları koyu yap
            bool isDark = IsDark(t.Background);
            SetRaw(res, "TextPrimaryBrush",   new SolidColorBrush(isDark ? Color.FromRgb(0xF0,0xF0,0xFF) : Color.FromRgb(0x1A,0x1A,0x2E)));
            SetRaw(res, "TextSecondaryBrush", new SolidColorBrush(isDark ? Color.FromRgb(0xA0,0xA0,0xC0) : Color.FromRgb(0x4A,0x4A,0x6A)));
            SetRaw(res, "TextMutedBrush",     new SolidColorBrush(isDark ? Color.FromRgb(0x60,0x60,0xA0) : Color.FromRgb(0x8A,0x8A,0xAA)));

            // Gradient güncelle
            var grad = new LinearGradientBrush
            {
                StartPoint = new Point(0, 0),
                EndPoint = new Point(1, 0)
            };
            grad.GradientStops.Add(new GradientStop((Color)ColorConverter.ConvertFromString(t.Accent), 0));
            grad.GradientStops.Add(new GradientStop((Color)ColorConverter.ConvertFromString(t.AccentSecondary), 1));
            res["AccentGradient"] = grad;
        }

        private static void Set(ResourceDictionary res, string key, string hex)
        {
            res[key] = new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));
        }

        private static void SetRaw(ResourceDictionary res, string key, SolidColorBrush brush)
        {
            res[key] = brush;
        }

        private static bool IsDark(string hex)
        {
            var c = (Color)ColorConverter.ConvertFromString(hex);
            return (c.R * 0.299 + c.G * 0.587 + c.B * 0.114) < 128;
        }
    }

    public record ThemeColors(
        string Background,
        string Surface,
        string SurfaceElevated,
        string Card,
        string Border,
        string Accent,
        string AccentSecondary
    );
}
