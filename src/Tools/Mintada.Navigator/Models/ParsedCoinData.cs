using System.Collections.Generic;

namespace Mintada.Navigator.Models
{
    public class ParsedCoinData
    {
        public string? Title { get; set; }
        public string? Subtitle { get; set; }
        public string? Issuer { get; set; }
        public string? YearText { get; set; }
        public string? ValueText { get; set; }
        public string? CurrencyText { get; set; }
        public string? Composition { get; set; }
        public string? WeightText { get; set; }
        public string? DiameterText { get; set; }
        public string? ThicknessText { get; set; }
        public string? Shape { get; set; }
        public string? Orientation { get; set; }
        public string? References { get; set; }
        public int? RulerId { get; set; }
        
        // DB Verification
        public string? DbRulerName { get; set; }
        public string? DbRulerYears { get; set; }
        public bool IsRulerVerified { get; set; }
        public bool NeedsInspection { get; set; }
        public int? DbShapeId { get; set; }

        // Dimensions Verification
        public decimal? DecimalWeight { get; set; }
        public decimal? DecimalDiameter { get; set; }
        public decimal? DecimalThickness { get; set; }
        public bool HasDimensionAlarm { get; set; }
        public string? DimensionAlarmMessage { get; set; }
    }
}
