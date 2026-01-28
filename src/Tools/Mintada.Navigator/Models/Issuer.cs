using System.Collections.Generic;
using System.ComponentModel; // For INotifyPropertyChanged
using System.Runtime.CompilerServices; // For CallerMemberName
using System.Text.Json.Serialization;

namespace Mintada.Navigator.Models
{
    public class Issuer : INotifyPropertyChanged
    {
        public long Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string UrlSlug { get; set; } = string.Empty;
        public string? ParentUrlSlug { get; set; }
        public string TerritoryType { get; set; } = string.Empty;
        
        [JsonIgnore]
        public List<Issuer> Children { get; set; } = new List<Issuer>();

        public bool HasNonReferenceSamples { get; set; }

        // UI State Properties
        private bool _isExpanded;
        [JsonIgnore]
        public bool IsExpanded
        {
            get => _isExpanded;
            set
            {
                if (_isExpanded != value)
                {
                    _isExpanded = value;
                    OnPropertyChanged();
                }
            }
        }

        private bool _isSelected;
        [JsonIgnore]
        public bool IsSelected
        {
            get => _isSelected;
            set
            {
                if (_isSelected != value)
                {
                    _isSelected = value;
                    OnPropertyChanged();
                }
            }
        }

        public event PropertyChangedEventHandler? PropertyChanged;

        protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        public override string ToString() => Name;
    }
}
