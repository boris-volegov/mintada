using System.Windows;

namespace Mintada.Navigator.Views
{
    public partial class AddCoinTypeDialog : Window
    {
        public AddCoinTypeDialog()
        {
            InitializeComponent();
        }

        public string CoinTypeIdText => CoinTypeIdTextBox.Text?.Trim() ?? string.Empty;

        public string CookieText => CookieTextBox.Text ?? string.Empty;

        public void SetData(string issuerName, string issuerSlug, string initialCoinTypeId, string initialCookie)
        {
            IssuerTextBlock.Text = $"{issuerName} ({issuerSlug})";
            CoinTypeIdTextBox.Text = initialCoinTypeId ?? string.Empty;
            CookieTextBox.Text = initialCookie ?? string.Empty;
            CoinTypeIdTextBox.Focus();
            CoinTypeIdTextBox.SelectAll();
        }

        private void Ok_Click(object sender, RoutedEventArgs e)
        {
            if (!long.TryParse(CoinTypeIdText, out var coinId) || coinId <= 0)
            {
                MessageBox.Show(
                    "Enter a valid positive coin type ID.",
                    "Invalid Coin ID",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
                CoinTypeIdTextBox.Focus();
                CoinTypeIdTextBox.SelectAll();
                return;
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
