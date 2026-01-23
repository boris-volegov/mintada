using System.Collections.Generic;

namespace Mintada.Navigator.Models
{
    public class RulerPeriodGroup
    {
        public string Period { get; set; } = string.Empty;
        public int PeriodOrder { get; set; }
        public List<Ruler> Rulers { get; set; } = new();
        public bool IsAssociated { get; set; }
        public bool IsPartiallyAssociated { get; set; }
    }
}
