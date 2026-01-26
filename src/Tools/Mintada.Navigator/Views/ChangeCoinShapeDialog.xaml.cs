using System.Collections.Generic;
using System.Linq;
using System.Windows;
using Mintada.Navigator.Models;

namespace Mintada.Navigator.Views
{
    public partial class ChangeCoinShapeDialog : Window
    {
        public CoinShape? SelectedShape => ShapesComboBox.SelectedItem as CoinShape;
        public string ShapeInfo => ShapeInfoTextBox.Text;
        public string WeightInfo => WeightInfoTextBox.Text;
        public string DiameterInfo => DiameterInfoTextBox.Text;
        public string ThicknessInfo => ThicknessInfoTextBox.Text;

        public ChangeCoinShapeDialog()
        {
            InitializeComponent();
        }

        public void SetData(List<CoinShape> shapes, int? currentShapeId, string? currentInfo, string? currentWeight, string? currentDiameter, string? currentThickness)
        {
            ShapesComboBox.ItemsSource = shapes;
            if (currentShapeId.HasValue)
            {
                ShapesComboBox.SelectedItem = shapes.FirstOrDefault(s => s.Id == currentShapeId.Value);
            }
            ShapeInfoTextBox.Text = currentInfo ?? string.Empty;
            WeightInfoTextBox.Text = currentWeight ?? string.Empty;
            DiameterInfoTextBox.Text = currentDiameter ?? string.Empty;
            ThicknessInfoTextBox.Text = currentThickness ?? string.Empty;
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
