using System;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;

namespace Mintada.Navigator.Views
{
    public partial class AddCoinTypeDialog : Window
    {
        private Func<long, Task<bool>>? _coinTypeExistsChecker;
        private CancellationTokenSource? _existsCheckCts;
        private long _existsCheckVersion;

        public AddCoinTypeDialog()
        {
            InitializeComponent();
            CoinTypeIdTextBox.TextChanged += CoinTypeIdTextBox_TextChanged;
        }

        public string CoinTypeIdText => CoinTypeIdTextBox.Text?.Trim() ?? string.Empty;

        public bool CoinTypeAlreadyExists { get; private set; }

        public void SetData(
            string issuerName,
            string issuerSlug,
            string initialCoinTypeId,
            Func<long, Task<bool>>? coinTypeExistsChecker = null
        )
        {
            _coinTypeExistsChecker = coinTypeExistsChecker;
            IssuerTextBlock.Text = $"{issuerName} ({issuerSlug})";
            CoinTypeIdTextBox.Text = initialCoinTypeId ?? string.Empty;
            CoinTypeIdTextBox.Focus();
            CoinTypeIdTextBox.SelectAll();
            _ = RefreshCoinExistsWarningAsync();
        }

        private async void Ok_Click(object sender, RoutedEventArgs e)
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

            CoinTypeAlreadyExists = await CheckCoinTypeExistsAsync(coinId);
            UpdateExistingWarning(CoinTypeAlreadyExists);

            DialogResult = true;
            Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }

        private void CoinTypeIdTextBox_TextChanged(object sender, TextChangedEventArgs e)
        {
            _ = RefreshCoinExistsWarningAsync();
        }

        private async Task RefreshCoinExistsWarningAsync()
        {
            var currentVersion = Interlocked.Increment(ref _existsCheckVersion);

            _existsCheckCts?.Cancel();
            _existsCheckCts?.Dispose();
            _existsCheckCts = new CancellationTokenSource();
            var token = _existsCheckCts.Token;

            var coinIdText = CoinTypeIdText;
            if (!long.TryParse(coinIdText, out var coinId) || coinId <= 0 || _coinTypeExistsChecker == null)
            {
                CoinTypeAlreadyExists = false;
                UpdateExistingWarning(false);
                return;
            }

            bool exists;
            try
            {
                exists = await _coinTypeExistsChecker(coinId);
            }
            catch
            {
                exists = false;
            }

            if (token.IsCancellationRequested || currentVersion != _existsCheckVersion)
            {
                return;
            }

            CoinTypeAlreadyExists = exists;
            UpdateExistingWarning(exists);
        }

        private async Task<bool> CheckCoinTypeExistsAsync(long coinId)
        {
            if (_coinTypeExistsChecker == null)
            {
                return false;
            }

            try
            {
                return await _coinTypeExistsChecker(coinId);
            }
            catch
            {
                return false;
            }
        }

        private void UpdateExistingWarning(bool isVisible)
        {
            ExistingCoinWarningTextBlock.Visibility = isVisible ? Visibility.Visible : Visibility.Collapsed;
        }
    }
}
