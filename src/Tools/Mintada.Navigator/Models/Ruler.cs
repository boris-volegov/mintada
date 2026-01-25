namespace Mintada.Navigator.Models
{
    public class Ruler
    {
        public long Id { get; set; }
        public long RowId { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Period { get; set; } = string.Empty;
        public string YearsText { get; set; } = string.Empty;
        public int PeriodOrder { get; set; }
        public int? SubperiodOrder { get; set; }
        public long? IssuerId { get; set; }
        public bool IsManual { get; set; }
        
        public bool IsPrimary { get; set; }

        public int StartYear
        {
            get
            {
                if (string.IsNullOrWhiteSpace(YearsText)) return int.MaxValue;
                
                // Simple parser: find first number
                var match = System.Text.RegularExpressions.Regex.Match(YearsText, @"\d+");
                if (match.Success && int.TryParse(match.Value, out int year))
                {
                    if (YearsText.Contains("BC", System.StringComparison.OrdinalIgnoreCase))
                    {
                        return -year;
                    }
                    return year;
                }
                return int.MaxValue;
            }
        }
    }
}
