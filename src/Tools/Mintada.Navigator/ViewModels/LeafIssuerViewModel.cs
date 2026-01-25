using CommunityToolkit.Mvvm.ComponentModel;
using Mintada.Navigator.Models;
using System.Collections.ObjectModel;
using System.Threading.Tasks;

namespace Mintada.Navigator.ViewModels
{
    public partial class LeafIssuerViewModel : ObservableObject
    {
        private readonly System.Func<long, Task<System.Collections.Generic.List<RulerPeriodGroup>>> _loadRulersAction;

        [ObservableProperty]
        private long _id;

        [ObservableProperty]
        private string _fullPath;

        [ObservableProperty]
        private ObservableCollection<RulerPeriodGroup> _rulers = new();

        [ObservableProperty]
        private bool _isExpanded;
        
        [ObservableProperty]
        private bool _isLoading;

        public LeafIssuerViewModel(long id, string fullPath, System.Func<long, Task<System.Collections.Generic.List<RulerPeriodGroup>>> loadRulersAction)
        {
            _id = id;
            _fullPath = fullPath;
            _loadRulersAction = loadRulersAction;
        }

        partial void OnIsExpandedChanged(bool value)
        {
            if (value && Rulers.Count == 0)
            {
               _ = LoadRulers();
            }
        }

        private async Task LoadRulers()
        {
             if (_loadRulersAction == null) return;
             
             IsLoading = true;
             try
             {
                 var rulers = await _loadRulersAction(Id);
                 Rulers = new ObservableCollection<RulerPeriodGroup>(rulers);
             }
             finally
             {
                 IsLoading = false;
             }
        }
    }
}
