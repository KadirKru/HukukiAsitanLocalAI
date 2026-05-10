using System.Windows;
using System.Windows.Threading;

namespace LegalAdvisorWPF;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        // WPF UI thread unhandled exception
        DispatcherUnhandledException += (s, ex) =>
        {
            MessageBox.Show(
                $"Uygulama hatası:\n\n{ex.Exception.Message}\n\n{ex.Exception.InnerException?.Message}",
                "Hata", MessageBoxButton.OK, MessageBoxImage.Error);
            ex.Handled = true; // Uygulamanın kapanmasını engelle
        };

        // Arka plan thread'lerdeki unhandled exception
        AppDomain.CurrentDomain.UnhandledException += (s, ex) =>
        {
            if (ex.ExceptionObject is Exception exception)
                MessageBox.Show($"Kritik hata:\n\n{exception.Message}",
                    "Kritik Hata", MessageBoxButton.OK, MessageBoxImage.Error);
        };

        // Task'larda yakalanmayan exception
        TaskScheduler.UnobservedTaskException += (s, ex) =>
        {
            MessageBox.Show($"Arka plan hatası:\n\n{ex.Exception.InnerException?.Message ?? ex.Exception.Message}",
                "Arka Plan Hatası", MessageBoxButton.OK, MessageBoxImage.Error);
            ex.SetObserved();
        };
    }
}
