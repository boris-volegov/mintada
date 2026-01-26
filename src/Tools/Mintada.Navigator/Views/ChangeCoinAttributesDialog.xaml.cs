using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using Mintada.Navigator.Models;

namespace Mintada.Navigator.Views
{
    public partial class ChangeCoinAttributesDialog : Window
    {
        public CoinShape? SelectedShape => ShapesComboBox.SelectedItem as CoinShape;
        
        public string ShapeInfo => ShapeInfoTextBox.Text;
        public string WeightInfo => WeightInfoTextBox.Text;
        public string DiameterInfo => DiameterInfoTextBox.Text;
        public string ThicknessInfo => ThicknessInfoTextBox.Text;

        public decimal? Weight => ParseDecimal(WeightTextBox.Text);
        public decimal? Diameter => ParseDecimal(DiameterTextBox.Text);
        public decimal? Thickness => ParseDecimal(ThicknessTextBox.Text);

        public ChangeCoinAttributesDialog()
        {
            InitializeComponent();
        }

        public void SetData(List<CoinShape> shapes, int? currentShapeId, 
            string? currentInfo, string? currentWeightInfo, string? currentDiameterInfo, string? currentThicknessInfo,
            decimal? currentWeight, decimal? currentDiameter, decimal? currentThickness)
        {
            ShapesComboBox.ItemsSource = shapes;
            if (currentShapeId.HasValue)
            {
                ShapesComboBox.SelectedItem = shapes.FirstOrDefault(s => s.Id == currentShapeId.Value);
            }
            
            ShapeInfoTextBox.Text = currentInfo ?? string.Empty;
            WeightInfoTextBox.Text = currentWeightInfo ?? string.Empty;
            DiameterInfoTextBox.Text = currentDiameterInfo ?? string.Empty;
            ThicknessInfoTextBox.Text = currentThicknessInfo ?? string.Empty;

            WeightTextBox.Text = currentWeight?.ToString() ?? string.Empty;
            DiameterTextBox.Text = currentDiameter?.ToString() ?? string.Empty;
            ThicknessTextBox.Text = currentThickness?.ToString() ?? string.Empty;
        }

        private decimal? ParseDecimal(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return null;
            if (decimal.TryParse(text, out var val)) return val;
            return null; // Or handle error
        }

        private void OkButton_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = true;
            Close();
        }

        private void CancelButton_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}
