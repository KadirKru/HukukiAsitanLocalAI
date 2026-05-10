using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;

namespace LegalAdvisorWPF.Views;

/// <summary>
/// Görsel renk paleti: kullanıcı hem palettten tıklayarak hem
/// de hex kodu yazarak renk seçebilir.
/// </summary>
public partial class ColorPickerWindow : Window
{
    public string? SelectedHex { get; private set; }

    // Tam ölçekli 200 renk paleti
    private static readonly string[] PaletteColors =
    {
        // Black to White Grayscale
        "#000000","#1c1c1c","#383838","#555555","#717171","#8d8d8d","#aaaaaa","#c6c6c6","#e2e2e2","#ffffff",
        // Slate, Gray
        "#0f172a","#1e293b","#334155","#475569","#64748b","#94a3b8","#cbd5e1","#e2e8f0","#f1f5f9","#f8fafc",
        "#111827","#1f2937","#374151","#4b5563","#6b7280","#9ca3af","#d1d5db","#e5e7eb","#f3f4f6","#f9fafb",
        // Red, Orange, Amber, Yellow
        "#450a0a","#7f1d1d","#991b1b","#b91c1c","#dc2626","#ef4444","#f87171","#fca5a5","#fecaca","#fee2e2",
        "#431407","#7c2d12","#9a3412","#c2410c","#ea580c","#f97316","#fb923c","#fdba74","#fed7aa","#ffedd5",
        "#451a03","#78350f","#92400e","#b45309","#d97706","#f59e0b","#fbbf24","#fcd34d","#fde68a","#fef3c7",
        "#422006","#713f12","#854d0e","#a16207","#ca8a04","#eab308","#facc15","#fde047","#fef08a","#fef9c3",
        // Lime, Green, Emerald, Teal
        "#1a2e05","#3f6212","#4d7c0f","#65a30d","#84cc16","#a3e635","#bef264","#d9f99d","#ecfccb","#f7fee7",
        "#052e16","#14532d","#166534","#15803d","#16a34a","#22c55e","#4ade80","#86efac","#bbf7d0","#dcfce7",
        "#022c22","#064e3b","#065f46","#047857","#059669","#10b981","#34d399","#6ee7b7","#a7f3d0","#d1fae5",
        "#042f2e","#134e4a","#115e59","#0f766e","#0d9488","#14b8a6","#2dd4bf","#5eead4","#99f6e4","#ccfbf1",
        // Cyan, Sky, Blue, Indigo
        "#083344","#164e63","#155e75","#0e7490","#0891b2","#06b6d4","#22d3ee","#67e8f9","#a5f3fc","#cffafe",
        "#0c4a6e","#075985","#0369a1","#0284c7","#0ea5e9","#38bdf8","#7dd3fc","#bae6fd","#e0f2fe","#f0f9ff",
        "#172554","#1e3a8a","#1e40af","#1d4ed8","#2563eb","#3b82f6","#60a5fa","#93c5fd","#bfdbfe","#dbeafe",
        "#312e81","#3730a3","#3f38cc","#4338ca","#4f46e5","#6366f1","#818cf8","#a5b4fc","#c7d2fe","#e0e7ff",
        // Violet, Purple, Fuchsia, Pink, Rose
        "#2e1065","#4c1d95","#5b21b6","#6d28d9","#7c3aed","#8b5cf6","#a78bfa","#c4b5fd","#ddd6fe","#ede9fe",
        "#3b0764","#581c87","#6b21a8","#7e22ce","#9333ea","#a855f7","#c084fc","#d8b4fe","#e9d5ff","#f3e8ff",
        "#4a044e","#701a75","#86198f","#a21caf","#c026d3","#d946ef","#e879f9","#f0abfc","#f5d0fe","#fae8ff",
        "#500724","#831843","#9d174d","#be185d","#db2777","#ec4899","#f472b6","#f9a8d4","#fbcfe8","#fce7f3",
        "#4c0519","#881337","#9f1239","#be123c","#e11d48","#f43f5e","#fb7185","#fda4af","#fecdd3","#ffe4e6"
    };

    public ColorPickerWindow(string currentHex)
    {
        Title           = "Renk Secin";
        Width           = 420;
        Height          = 340;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        ResizeMode      = ResizeMode.NoResize;
        Background      = new SolidColorBrush(Color.FromRgb(0x16, 0x21, 0x3E));
        SelectedHex     = currentHex;

        var root = new Grid { Margin = new Thickness(14) };
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        // Başlık
        var lbl = new TextBlock
        {
            Text       = "Renk paleti veya hex kodu girebilirsiniz",
            FontSize   = 11,
            Foreground = new SolidColorBrush(Colors.LightGray),
            Margin     = new Thickness(0, 0, 0, 10)
        };
        Grid.SetRow(lbl, 0);
        root.Children.Add(lbl);

        // Palet ızgarası
        var paletteScroll = new ScrollViewer
        {
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            Margin = new Thickness(0, 0, 0, 10)
        };
        var palette = new System.Windows.Controls.Primitives.UniformGrid
        {
            Columns = 10,
            HorizontalAlignment = HorizontalAlignment.Center
        };

        foreach (var hex in PaletteColors)
        {
            var rect = new Rectangle
            {
                Width        = 26,
                Height       = 26,
                Margin       = new Thickness(2),
                RadiusX      = 4,
                RadiusY      = 4,
                Fill         = new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex)),
                Cursor       = Cursors.Hand,
                ToolTip      = hex,
                Stroke       = new SolidColorBrush(Color.FromArgb(0x55, 0xFF, 0xFF, 0xFF)),
                StrokeThickness = 1
            };
            var capturedHex = hex;
            rect.MouseLeftButtonUp += (s, _) =>
            {
                SelectedHex = capturedHex;
                HexBox.Text = capturedHex;
                Preview.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString(capturedHex));
                // Seçili rengin kenarlığını belirginleştir
                if (s is Rectangle r) r.StrokeThickness = 2.5;
            };
            rect.MouseEnter += (s, _) =>
            {
                if (s is Rectangle r) r.Opacity = 0.8;
            };
            rect.MouseLeave += (s, _) =>
            {
                if (s is Rectangle r) r.Opacity = 1.0;
            };
            palette.Children.Add(rect);
        }
        paletteScroll.Content = palette;
        Grid.SetRow(paletteScroll, 1);
        root.Children.Add(paletteScroll);

        // Alt satır: önizleme + hex giriş + butonlar
        var botPanel = new Grid();
        botPanel.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        botPanel.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        botPanel.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        botPanel.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        Preview = new Rectangle
        {
            Width        = 34,
            Height       = 34,
            RadiusX      = 6,
            RadiusY      = 6,
            Margin       = new Thickness(0, 0, 8, 0),
            Fill         = new SolidColorBrush((Color)ColorConverter.ConvertFromString(currentHex)),
            Stroke       = new SolidColorBrush(new SolidColorBrush(Colors.White) { Opacity = 0.3 }.Color),
            StrokeThickness = 1
        };
        Grid.SetColumn(Preview, 0);

        HexBox = new TextBox
        {
            Text            = currentHex,
            FontSize        = 13,
            Background      = new SolidColorBrush(Color.FromRgb(0x0A, 0x0A, 0x14)),
            Foreground      = new SolidColorBrush(Colors.White),
            BorderBrush     = new SolidColorBrush(Color.FromRgb(0x2D, 0x2D, 0x5E)),
            BorderThickness = new Thickness(1),
            Padding         = new Thickness(8, 4, 8, 4),
            Margin          = new Thickness(0, 0, 8, 0),
            VerticalAlignment = VerticalAlignment.Center
        };
        HexBox.TextChanged += (_, _) =>
        {
            try
            {
                var c = (Color)ColorConverter.ConvertFromString(HexBox.Text);
                Preview.Fill = new SolidColorBrush(c);
                SelectedHex  = HexBox.Text;
            }
            catch { }
        };
        Grid.SetColumn(HexBox, 1);

        var btnOk = MakeBtn("Uygula", Color.FromRgb(0x6C, 0x63, 0xFF));
        btnOk.Click += (_, _) => { SelectedHex = HexBox.Text; DialogResult = true; };
        Grid.SetColumn(btnOk, 2);

        var btnCancel = MakeBtn("Iptal", Color.FromRgb(0x2D, 0x2D, 0x5E));
        btnCancel.Click += (_, _) => { DialogResult = false; };
        btnCancel.Margin = new Thickness(6, 0, 0, 0);
        Grid.SetColumn(btnCancel, 3);

        botPanel.Children.Add(Preview);
        botPanel.Children.Add(HexBox);
        botPanel.Children.Add(btnOk);
        botPanel.Children.Add(btnCancel);

        Grid.SetRow(botPanel, 2);
        root.Children.Add(botPanel);

        Content = root;
    }

    // Named fields set in constructor - needed for TextChanged handler
    private readonly Rectangle Preview;
    private readonly TextBox HexBox;

    private static Button MakeBtn(string text, Color bg) => new()
    {
        Content         = text,
        Background      = new SolidColorBrush(bg),
        Foreground      = new SolidColorBrush(Colors.White),
        BorderThickness = new Thickness(0),
        Padding         = new Thickness(14, 6, 14, 6),
        FontSize        = 12,
        Cursor          = Cursors.Hand,
        Template        = CreateBtnTemplate()
    };

    private static ControlTemplate CreateBtnTemplate()
    {
        var tpl = new ControlTemplate(typeof(Button));
        var border = new FrameworkElementFactory(typeof(Border));
        border.SetBinding(Border.BackgroundProperty, new System.Windows.Data.Binding { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent), Path = new PropertyPath("Background") });
        border.SetValue(Border.CornerRadiusProperty, new CornerRadius(6));
        border.SetBinding(Border.PaddingProperty, new System.Windows.Data.Binding { RelativeSource = new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent), Path = new PropertyPath("Padding") });
        var cp = new FrameworkElementFactory(typeof(ContentPresenter));
        cp.SetValue(FrameworkElement.HorizontalAlignmentProperty, HorizontalAlignment.Center);
        cp.SetValue(FrameworkElement.VerticalAlignmentProperty, VerticalAlignment.Center);
        border.AppendChild(cp);
        tpl.VisualTree = border;
        return tpl;
    }
}
