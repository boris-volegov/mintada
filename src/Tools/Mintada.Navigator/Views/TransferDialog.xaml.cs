using System;
using System.Windows;
using System.ComponentModel;
using System.Windows.Media.Imaging;
using Mintada.Navigator.ViewModels;
using Mintada.Navigator.Converters;

namespace Mintada.Navigator.Views
{
    public partial class TransferDialog : Window
    {
        private MainViewModel? _viewModel;

        public TransferDialog()
        {
            InitializeComponent();
            Closed += TransferDialog_Closed;
        }

        public void SetViewModel(MainViewModel viewModel)
        {
            _viewModel = viewModel;
            DataContext = viewModel;
            
            // Subscribe to PropertyChanged to ensure UI updates
            viewModel.PropertyChanged += ViewModel_PropertyChanged;
        }

        private void ViewModel_PropertyChanged(object? sender, PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(MainViewModel.TransferTargetCoin))
            {
                System.Diagnostics.Debug.WriteLine($"TransferDialog: PropertyChanged for TransferTargetCoin");
                UpdateTargetCoinDisplay();
            }
        }

        private void UpdateTargetCoinDisplay()
        {
            if (_viewModel?.TransferTargetCoin == null)
            {
                TargetInfoPanel.Visibility = Visibility.Collapsed;
                PlaceholderText.Visibility = Visibility.Visible;
                return;
            }

            var target = _viewModel.TransferTargetCoin;
            
            // Show the info panel
            TargetInfoPanel.Visibility = Visibility.Visible;
            PlaceholderText.Visibility = Visibility.Collapsed;
            
            // Set text values
            TargetTitle.Text = target.Title ?? "";
            TargetSubtitle.Text = target.Subtitle ?? "";
            SamplesCount.Text = $"Samples: {target.Samples?.Count ?? 0}";
            
            // Set images
            if (target.Samples != null && target.Samples.Count > 0)
            {
                var sample = target.Samples[0];
                
                // Load obverse image
                var obversePath = sample.ObversePath;
                ImagePath.Text = $"Obverse: {obversePath}";
                
                if (!string.IsNullOrEmpty(obversePath))
                {
                    System.Diagnostics.Debug.WriteLine($"Loading obverse from: {obversePath}");
                    System.Diagnostics.Debug.WriteLine($"File exists: {System.IO.File.Exists(obversePath)}");
                    
                    try
                    {
                        var bitmap = PathToBitmapImageConverter.Instance.Convert(obversePath, null, null, null) as BitmapImage;
                        if (bitmap != null)
                        {
                            TargetImage.Source = bitmap;
                            System.Diagnostics.Debug.WriteLine($"Obverse loaded: {bitmap.PixelWidth}x{bitmap.PixelHeight}");
                        }
                        else
                        {
                            var bitmapImage = new BitmapImage();
                            bitmapImage.BeginInit();
                            bitmapImage.UriSource = new Uri(obversePath, UriKind.Absolute);
                            bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
                            bitmapImage.EndInit();
                            TargetImage.Source = bitmapImage;
                        }
                    }
                    catch (Exception ex)
                    {
                        System.Diagnostics.Debug.WriteLine($"Failed to load obverse: {ex.Message}");
                    }
                }
                
                // Load reverse image
                var reversePath = sample.ReversePath;
                if (!string.IsNullOrEmpty(reversePath))
                {
                    System.Diagnostics.Debug.WriteLine($"Loading reverse from: {reversePath}");
                    
                    try
                    {
                        var bitmap = PathToBitmapImageConverter.Instance.Convert(reversePath, null, null, null) as BitmapImage;
                        if (bitmap != null)
                        {
                            TargetImageReverse.Source = bitmap;
                            System.Diagnostics.Debug.WriteLine($"Reverse loaded: {bitmap.PixelWidth}x{bitmap.PixelHeight}");
                        }
                        else
                        {
                            var bitmapImage = new BitmapImage();
                            bitmapImage.BeginInit();
                            bitmapImage.UriSource = new Uri(reversePath, UriKind.Absolute);
                            bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
                            bitmapImage.EndInit();
                            TargetImageReverse.Source = bitmapImage;
                        }
                    }
                    catch (Exception ex)
                    {
                        System.Diagnostics.Debug.WriteLine($"Failed to load reverse: {ex.Message}");
                    }
                }
            }
            else
            {
                ImagePath.Text = "(No samples)";
            }
        }

        private async void Confirm_Click(object sender, RoutedEventArgs e)
        {
            if (_viewModel != null)
            {
                await _viewModel.ConfirmTransferCommand.ExecuteAsync(null);
                Close();
            }
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void TransferDialog_Closed(object? sender, System.EventArgs e)
        {
            // Unsubscribe from events
            if (_viewModel != null)
            {
                _viewModel.PropertyChanged -= ViewModel_PropertyChanged;
                _viewModel.IsTransferModeActive = false;
                _viewModel.TransferTargetCoin = null;
                _viewModel.StatusMessage = "Transfer cancelled.";
            }
        }
    }
}
