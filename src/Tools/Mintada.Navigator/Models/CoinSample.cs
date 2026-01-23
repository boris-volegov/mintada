using CommunityToolkit.Mvvm.ComponentModel;

namespace Mintada.Navigator.Models
{
    public partial class CoinSample : ObservableObject
    {
        public CoinSample(string? obverse, string? reverse, int type)
        {
            ObverseImage = obverse;
            ReverseImage = reverse;
            SampleType = type;
        }

        public string? ObverseImage { get; set; }
        public string? ReverseImage { get; set; }
        public int SampleType { get; set; }
        
        [ObservableProperty]
        [NotifyPropertyChangedFor(nameof(HasObverse))]
        [NotifyPropertyChangedFor(nameof(IsCombinedImage))]
        private string _obversePath = string.Empty;

        [ObservableProperty]
        [NotifyPropertyChangedFor(nameof(HasReverse))]
        [NotifyPropertyChangedFor(nameof(IsCombinedImage))]
        private string _reversePath = string.Empty;

        public bool IsReference => SampleType == 1;
        
        public bool HasObverse => !string.IsNullOrEmpty(ObversePath);
        public bool HasReverse => !string.IsNullOrEmpty(ReversePath);

        public bool IsCombinedImage 
        {
            get 
            {
                 if (!HasObverse || !HasReverse) return false;
                 if (string.Equals(ObverseImage?.Trim(), ReverseImage?.Trim(), System.StringComparison.OrdinalIgnoreCase)) return true;
                 if (string.Equals(ObversePath?.Trim(), ReversePath?.Trim(), System.StringComparison.OrdinalIgnoreCase)) return true;
                 return false;
            }
        }

        // Visual helper for combined image line
        [ObservableProperty]
        private double _splitRatio = 0.5;

        [ObservableProperty]
        private bool _isSwapSuggested;

        [ObservableProperty]
        private bool _isHolder;

        [ObservableProperty]
        private bool _isCounterstamped;

        [ObservableProperty]
        private bool _isRoll;

        [ObservableProperty]
        private bool _containsHolder;

        [ObservableProperty]
        private bool _containsText;

        [ObservableProperty]
        private bool _isMultiCoin;

        [ObservableProperty]
        private bool _isSelected;

        public ulong? DHash { get; set; }

        [ObservableProperty]
        [NotifyPropertyChangedFor(nameof(IsFuzzyGrouped))]
        private int? _fuzzyGroupIndex;

        public bool IsFuzzyGrouped => FuzzyGroupIndex.HasValue;
    }
}
