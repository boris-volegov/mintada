namespace Mintada.Navigator.Models
{
    public class RulerOption
    {
        public long Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string? RuleType { get; set; }
        public int? StartYear { get; set; }
        public int? EndYear { get; set; }
        public bool? IsApprox { get; set; }
    }
}
