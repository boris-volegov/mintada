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
    }
}
