namespace Mintada.Navigator.Models
{
    public class CoinType
    {
        public long Id { get; set; }
        public long IssuerId { get; set; }
        public string Title { get; set; } = string.Empty;
        public string? Subtitle { get; set; }
        public string CoinTypeSlug { get; set; } = string.Empty;
        public string? Period { get; set; }
        public string IssuerUrlSlug { get; set; } = string.Empty;
        public bool IsFixed { get; set; }
        public int? ShapeId { get; set; }
        public string? ShapeInfo { get; set; }
        public string? WeightInfo { get; set; }
        public string? DiameterInfo { get; set; }
        public string? ThicknessInfo { get; set; }
        public decimal? Weight { get; set; }
        public decimal? Diameter { get; set; }
        public decimal? Thickness { get; set; }
        public string? Size { get; set; }
        public string? DenominationText { get; set; }
        public decimal? ValueAmount { get; set; }
        public string? DenominationInfo1 { get; set; }
        public decimal? ValueAmountUsd { get; set; }
        public string? ValueCurrencySymbol { get; set; }
        public string? DenominationAlt { get; set; }
        public string? StartDate { get; set; }
        public string? EndDate { get; set; }
        public string? StartNativeDate { get; set; }
        public string? EndNativeDate { get; set; }
        public string? StartMintDate { get; set; }
        public string? EndMintDate { get; set; }
        public string? RestrikeDate { get; set; }
        public string? RestrikeStartMintDate { get; set; }
        public string? RestrikeEndMintDate { get; set; }
        public string? ErroneousDates { get; set; }
        public int? CalendarSystemId { get; set; }
        public int? PeriodId { get; set; }
        public System.Collections.ObjectModel.ObservableCollection<CoinSample> Samples { get; set; } = new();
        
        // Helper for view binding
        public IEnumerable<CoinSample> NonReferenceSamples => Samples.Where(s => !s.IsReference);
        public CoinSample? ReferenceSample => Samples.FirstOrDefault(s => s.IsReference);
    }
}
