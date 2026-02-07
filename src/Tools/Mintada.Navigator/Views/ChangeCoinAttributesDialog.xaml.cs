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
        public CalendarSystem? SelectedCalendarSystem => CalendarSystemComboBox.SelectedItem as CalendarSystem;
        public Period? SelectedPeriod => PeriodsComboBox.SelectedItem as Period;
        public RulerOption? SelectedRuler1 => Ruler1ComboBox.SelectedItem as RulerOption;
        public RulerOption? SelectedRuler2 => Ruler2ComboBox.SelectedItem as RulerOption;
        public RulerOption? SelectedRuler3 => Ruler3ComboBox.SelectedItem as RulerOption;

        public List<RulerOption> SelectedRulers => new[] { SelectedRuler1, SelectedRuler2, SelectedRuler3 }
            .Where(r => r != null)
            .Select(r => r!)
            .GroupBy(r => r.Id)
            .Select(g => g.First())
            .ToList();
        
        public string ShapeInfo => ShapeInfoTextBox.Text;
        public string WeightInfo => WeightInfoTextBox.Text;
        public string DiameterInfo => DiameterInfoTextBox.Text;
        public string ThicknessInfo => ThicknessInfoTextBox.Text;

        public decimal? Weight => ParseDecimal(WeightTextBox.Text);
        public decimal? Diameter => ParseDecimal(DiameterTextBox.Text);
        public decimal? Thickness => ParseDecimal(ThicknessTextBox.Text);
        public string Size => SizeTextBox.Text;

        public string DenominationText => DenominationTextBox.Text;
        public decimal? ValueAmount => ParseDecimal(ValueAmountTextBox.Text);
        public string DenominationInfo1 => DenominationInfo1TextBox.Text;
        public decimal? ValueAmountUsd => ParseDecimal(ValueAmountUsdTextBox.Text);
        public string ValueCurrencySymbol => ValueCurrencySymbolTextBox.Text;
        public string DenominationAlt => DenominationAltTextBox.Text;

        public string StartDate => StartDateTextBox.Text;
        public string EndDate => EndDateTextBox.Text;
        public string StartNativeDate => StartNativeDateTextBox.Text;
        public string EndNativeDate => EndNativeDateTextBox.Text;
        public string StartMintDate => StartMintDateTextBox.Text;
        public string EndMintDate => EndMintDateTextBox.Text;

        public string RestrikeDate => RestrikeDateTextBox.Text;
        public string RestrikeStartMintDate => RestrikeStartMintDateTextBox.Text;
        public string RestrikeEndMintDate => RestrikeEndMintDateTextBox.Text;
        public string ErroneousDates => ErroneousDatesTextBox.Text;

        public event EventHandler? RequestSave;

        public ChangeCoinAttributesDialog()
        {
            InitializeComponent();
        }

        public void SetData(List<CoinShape> shapes, int? currentShapeId, 
            string? currentInfo, string? currentWeightInfo, string? currentDiameterInfo, string? currentThicknessInfo,
            decimal? currentWeight, decimal? currentDiameter, decimal? currentThickness, string? currentSize,
            string? currentDenominationText, decimal? currentValueAmount, string? currentDenominationInfo1, decimal? currentValueAmountUsd, string? currentValueCurrencySymbol, string? currentDenominationAlt,
            string? currentStartDate, string? currentEndDate, string? currentStartNativeDate, string? currentEndNativeDate, string? currentStartMintDate, string? currentEndMintDate,
            string? currentRestrikeDate, string? currentRestrikeStartMintDate, string? currentRestrikeEndMintDate, string? currentErroneousDates,
            List<CalendarSystem> calendarSystems, int? currentCalendarSystemId, List<Period> periods, int? currentPeriodId,
            List<RulerOption> rulerOptions)
        {
            ShapesComboBox.ItemsSource = shapes;
            if (currentShapeId.HasValue)
            {
                ShapesComboBox.SelectedItem = shapes.FirstOrDefault(s => s.Id == currentShapeId.Value);
            }

            CalendarSystemComboBox.ItemsSource = calendarSystems;
            if (currentCalendarSystemId.HasValue)
            {
                CalendarSystemComboBox.SelectedItem = calendarSystems.FirstOrDefault(s => s.Id == currentCalendarSystemId.Value);
            }

            PeriodsComboBox.ItemsSource = periods;
            if (currentPeriodId.HasValue)
            {
                PeriodsComboBox.SelectedItem = periods.FirstOrDefault(p => p.Id == currentPeriodId.Value);
            }

            Ruler1ComboBox.ItemsSource = rulerOptions;
            Ruler2ComboBox.ItemsSource = rulerOptions;
            Ruler3ComboBox.ItemsSource = rulerOptions;

            Ruler1ComboBox.SelectedItem = rulerOptions.ElementAtOrDefault(0);
            Ruler2ComboBox.SelectedItem = rulerOptions.ElementAtOrDefault(1);
            Ruler3ComboBox.SelectedItem = rulerOptions.ElementAtOrDefault(2);
            
            ShapeInfoTextBox.Text = currentInfo ?? string.Empty;
            WeightInfoTextBox.Text = currentWeightInfo ?? string.Empty;
            DiameterInfoTextBox.Text = currentDiameterInfo ?? string.Empty;
            ThicknessInfoTextBox.Text = currentThicknessInfo ?? string.Empty;

            WeightTextBox.Text = currentWeight?.ToString() ?? string.Empty;
            DiameterTextBox.Text = currentDiameter?.ToString() ?? string.Empty;
            ThicknessTextBox.Text = currentThickness?.ToString() ?? string.Empty;
            SizeTextBox.Text = currentSize ?? string.Empty;
            
            DenominationTextBox.Text = currentDenominationText ?? string.Empty;
            ValueAmountTextBox.Text = currentValueAmount?.ToString() ?? string.Empty;
            DenominationInfo1TextBox.Text = currentDenominationInfo1 ?? string.Empty;
            ValueAmountUsdTextBox.Text = currentValueAmountUsd?.ToString() ?? string.Empty;
            ValueCurrencySymbolTextBox.Text = currentValueCurrencySymbol ?? string.Empty;
            DenominationAltTextBox.Text = currentDenominationAlt ?? string.Empty;

            StartDateTextBox.Text = currentStartDate ?? string.Empty;
            EndDateTextBox.Text = currentEndDate ?? string.Empty;
            StartNativeDateTextBox.Text = currentStartNativeDate ?? string.Empty;
            EndNativeDateTextBox.Text = currentEndNativeDate ?? string.Empty;
            StartMintDateTextBox.Text = currentStartMintDate ?? string.Empty;
            EndMintDateTextBox.Text = currentEndMintDate ?? string.Empty;

            RestrikeDateTextBox.Text = currentRestrikeDate ?? string.Empty;
            RestrikeStartMintDateTextBox.Text = currentRestrikeStartMintDate ?? string.Empty;
            RestrikeEndMintDateTextBox.Text = currentRestrikeEndMintDate ?? string.Empty;
            ErroneousDatesTextBox.Text = currentErroneousDates ?? string.Empty;
        }

        private decimal? ParseDecimal(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return null;
            if (decimal.TryParse(text, out var val)) return val;
            return null; // Or handle error
        }

        private void OkButton_Click(object sender, RoutedEventArgs e)
        {
            RequestSave?.Invoke(this, EventArgs.Empty);
        }

        private void CancelButton_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void MoveNativeMintButton_Click(object sender, RoutedEventArgs e)
        {
            var s = StartDateTextBox.Text;
            var e_date = EndDateTextBox.Text;
            
            var sn = StartNativeDateTextBox.Text;
            var en = EndNativeDateTextBox.Text;
            var sm = StartMintDateTextBox.Text;
            var em = EndMintDateTextBox.Text;

            bool hasNative = !string.IsNullOrWhiteSpace(sn) || !string.IsNullOrWhiteSpace(en);
            bool hasMint = !string.IsNullOrWhiteSpace(sm) || !string.IsNullOrWhiteSpace(em);

            if (hasNative && !hasMint)
            {
                // Native populated, Mint empty
                // 1. Move Start/End -> Mint
                StartMintDateTextBox.Text = s;
                EndMintDateTextBox.Text = e_date;
                
                // 2. Move Native -> Start/End
                StartDateTextBox.Text = sn;
                EndDateTextBox.Text = en;
                
                // 3. Clear Native
                StartNativeDateTextBox.Text = string.Empty;
                EndNativeDateTextBox.Text = string.Empty;
            }
            else if (hasMint && !hasNative)
            {
                // Mint populated, Native empty
                // 1. Move Start/End -> Native
                StartNativeDateTextBox.Text = s;
                EndNativeDateTextBox.Text = e_date;
                
                // 2. Move Mint -> Start/End
                StartDateTextBox.Text = sm;
                EndDateTextBox.Text = em;
                
                // 3. Clear Mint
                StartMintDateTextBox.Text = string.Empty;
                EndMintDateTextBox.Text = string.Empty;
            }
            else
            {
                // Swap Native <-> Mint (Fallback)
                StartNativeDateTextBox.Text = sm;
                EndNativeDateTextBox.Text = em;
                StartMintDateTextBox.Text = sn;
                EndMintDateTextBox.Text = en;
            }
        }
    }
}
