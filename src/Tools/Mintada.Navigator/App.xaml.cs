using System.Configuration;
using System.Data;
using System.Windows;

namespace Mintada.Navigator;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    public App()
    {
        this.DispatcherUnhandledException += App_DispatcherUnhandledException;
    }

    private void App_DispatcherUnhandledException(object sender, System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
    {
        MessageBox.Show(e.Exception.ToString(), "Application Error", MessageBoxButton.OK, MessageBoxImage.Error);
        e.Handled = true;
    }
}

