using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;

namespace Mintada.Navigator;

/// <summary>
/// Interaction logic for MainWindow.xaml
/// </summary>
public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
    }

    private bool _isDraggingSplitLine;
    private Models.CoinSample? _draggingSample;

    private void TreeView_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
    {
        if (DataContext is ViewModels.MainViewModel viewModel && e.NewValue is Models.Issuer issuer)
        {
            viewModel.SelectedIssuer = issuer;
        }
    }

    private void SplitLine_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (sender is FrameworkElement element && element.Tag is Models.CoinSample sample)
        {
            _isDraggingSplitLine = true;
            _draggingSample = sample;
             element.CaptureMouse();
             e.Handled = true;
        }
    }

    private void SplitLine_MouseMove(object sender, MouseEventArgs e)
    {
        if (_isDraggingSplitLine && _draggingSample != null && sender is FrameworkElement element)
        {
             // Find the parent Canvas or Grid to calculate relative position
             // The visual tree is: Rectangle -> Canvas -> Grid (which contains Image)
             // We need coordinates relative to the Image (or the Grid wrapping it) to get 0..1 ratio
             
             if (VisualTreeHelper.GetParent(element) is Canvas canvas && VisualTreeHelper.GetParent(canvas) is Grid grid)
             {
                 // Find the Image in the grid to be sure of width?
                 // Actually grid width should correspond to image width if auto/stretch.
                 // Let's use the Grid's ActualWidth which matches the Image width ideally.
                 
                 var pos = e.GetPosition(grid);
                 var width = grid.ActualWidth;
                 
                 if (width > 0)
                 {
                     double newRatio = pos.X / width;
                     
                     // Clamp
                     if (newRatio < 0.0) newRatio = 0.0;
                     if (newRatio > 1.0) newRatio = 1.0;
                     
                     _draggingSample.SplitRatio = newRatio;
                 }
             }
        }
    }

    private void SplitLine_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (_isDraggingSplitLine)
        {
            _isDraggingSplitLine = false;
            _draggingSample = null;
            if (sender is FrameworkElement element)
            {
                element.ReleaseMouseCapture();
            }
        }
    }

    private void ListBox_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        // Support Ctrl+Left/Right to move split line
        if ((Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control)
        {
            if (e.Key == Key.Left || e.Key == Key.Right)
            {
                if (DataContext is ViewModels.MainViewModel vm && vm.SelectedSample != null && vm.SelectedSample.IsCombinedImage)
                {
                    double current = vm.SelectedSample.SplitRatio;
                    double step = 0.005; // 0.5% increment
                    
                    if (e.Key == Key.Left) current -= step;
                    else current += step;
                    
                    if (current < 0) current = 0;
                    if (current > 1) current = 1;

                    vm.SelectedSample.SplitRatio = current;
                    e.Handled = true;
                }
            }
        }
    }

    private void ListBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (DataContext is ViewModels.MainViewModel viewModel && sender is ListBox listBox)
        {
            viewModel.SelectedSamples.Clear();
            foreach (var item in listBox.SelectedItems)
            {
                if (item is Models.CoinSample sample)
                {
                    viewModel.SelectedSamples.Add(sample);
                }
            }
            
            // Re-evaluate commands
            viewModel.SplitSampleCommand.NotifyCanExecuteChanged();
            viewModel.SwapSampleCommand.NotifyCanExecuteChanged();
            viewModel.ChooseBestSampleCommand.NotifyCanExecuteChanged();
            viewModel.PromoteSampleCommand.NotifyCanExecuteChanged();
            viewModel.DeleteSampleCommand.NotifyCanExecuteChanged();
            viewModel.TransferSampleCommand.NotifyCanExecuteChanged();
            viewModel.MarkAsSampleCommand.NotifyCanExecuteChanged();
        }
    }

    private void ListBoxItem_MouseDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (sender is ListBoxItem item && item.DataContext is Models.CoinSample sample && DataContext is ViewModels.MainViewModel vm)
        {
             if (sample.IsFuzzyGrouped && sample.FuzzyGroupIndex.HasValue)
             {
                 // Select all in this group
                 // We need to access the ListBox to update SelectedItems.
                 // Walk up tree to find ListBox?
                 var listBox = ItemsControl.ItemsControlFromItemContainer(item) as ListBox;
                 if (listBox != null)
                 {
                     // Find all items with same GroupIndex
                     var groupMembers = listBox.Items.OfType<Models.CoinSample>()
                                         .Where(s => s.FuzzyGroupIndex == sample.FuzzyGroupIndex.Value)
                                         .ToList();
                                         
                     foreach(var member in groupMembers)
                     {
                         if (!listBox.SelectedItems.Contains(member))
                         {
                             listBox.SelectedItems.Add(member);
                         }
                     }
                 }
                 e.Handled = true;
             }
        }
    }
}