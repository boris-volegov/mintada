using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using Mintada.Navigator.Models;
using Mintada.Navigator.ViewModels;

namespace Mintada.Navigator.Views
{
    public partial class MarkAsDialog : Window
    {
        private MainViewModel? _viewModel;
        private List<CoinSample> _samples = new();
        private CheckBox[] _categoryCheckboxes = null!;

        public MarkAsDialog()
        {
            InitializeComponent();
            
            // Store references to all category checkboxes for easy iteration
            _categoryCheckboxes = new[]
            {
                HolderCheckbox,
                CounterstampedCheckbox,
                RollCheckbox,
                ContainsHolderCheckbox,
                ContainsTextCheckbox,
                MultiCoinCheckbox
            };
        }

        public void SetViewModel(MainViewModel viewModel, List<CoinSample> samples)
        {
            _viewModel = viewModel;
            _samples = samples;
            
            // Load current state from the first sample (they should all have the same markings if multiple selected)
            if (samples.Any())
            {
                var firstSample = samples[0];
                HolderCheckbox.IsChecked = firstSample.IsHolder;
                CounterstampedCheckbox.IsChecked = firstSample.IsCounterstamped;
                RollCheckbox.IsChecked = firstSample.IsRoll;
                ContainsHolderCheckbox.IsChecked = firstSample.ContainsHolder;
                ContainsTextCheckbox.IsChecked = firstSample.ContainsText;
                MultiCoinCheckbox.IsChecked = firstSample.IsMultiCoin;
            }
            
            UpdateStatusText();
        }

        private void Category_Checked(object sender, RoutedEventArgs e)
        {
            if (sender is CheckBox checkedBox)
            {
                // Uncheck all other checkboxes (mutual exclusivity)
                foreach (var checkbox in _categoryCheckboxes)
                {
                    if (checkbox != checkedBox && checkbox.IsChecked == true)
                    {
                        checkbox.IsChecked = false;
                    }
                }
            }
            
            UpdateStatusText();
        }

        private void Category_Unchecked(object sender, RoutedEventArgs e)
        {
            UpdateStatusText();
        }

        private void UpdateStatusText()
        {
            var checkedCount = _categoryCheckboxes.Count(cb => cb.IsChecked == true);
            
            if (checkedCount == 0)
            {
                StatusText.Text = "No category selected";
            }
            else if (checkedCount == 1)
            {
                var checkedBox = _categoryCheckboxes.First(cb => cb.IsChecked == true);
                StatusText.Text = $"Selected: {checkedBox.Content}";
            }
            else
            {
                StatusText.Text = "Multiple categories selected (only one allowed)";
            }
        }

        private async void Save_Click(object sender, RoutedEventArgs e)
        {
            if (_viewModel == null) return;
            
            // Apply the markings to all selected samples
            foreach (var sample in _samples)
            {
                sample.IsHolder = HolderCheckbox.IsChecked == true;
                sample.IsCounterstamped = CounterstampedCheckbox.IsChecked == true;
                sample.IsRoll = RollCheckbox.IsChecked == true;
                sample.ContainsHolder = ContainsHolderCheckbox.IsChecked == true;
                sample.ContainsText = ContainsTextCheckbox.IsChecked == true;
                sample.IsMultiCoin = MultiCoinCheckbox.IsChecked == true;
                
                // Save to database
                await _viewModel.SaveSampleMarkings(sample);
            }
            
            DialogResult = true;
            Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}
