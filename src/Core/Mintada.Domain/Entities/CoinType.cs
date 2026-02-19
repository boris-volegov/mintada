using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("coin_types")]
public class CoinType : BaseEntity
{
    public int IssuerId { get; set; }
    public Issuer Issuer { get; set; } = null!;

    public string Title { get; set; } = null!;
    public string? Subtitle { get; set; }
    public string? EdgeImage { get; set; }

    public int? ShapeId { get; set; }
    public Shape? Shape { get; set; }

    public int? CoinagePeriodId { get; set; }
    public CoinagePeriod? CoinagePeriod { get; set; }

    public int? RarityIndex { get; set; }
    public string UrlSlug { get; set; } = null!;
    public DateTime DateTimeInserted { get; set; }

    public int IssueTypeId { get; set; }
    public IssueType? IssueType { get; set; }
    public IssuerIssueTypeRel? IssuerIssueType { get; set; }
    public int? CalendarSystemId { get; set; }
    public CalendarSystem? CalendarSystem { get; set; }

    public decimal? Weight { get; set; }
    public decimal? Diameter { get; set; }
    public decimal? Thickness { get; set; }
    public string? Size { get; set; }
    public string? DenominationText { get; set; }
    public string? DenominationUnit { get; set; }
    public int? StartDate { get; set; }
    public int? EndDate { get; set; }
    public int? StartNativeDate { get; set; }
    public int? EndNativeDate { get; set; }
    public int? StartMintDate { get; set; }
    public int? EndMintDate { get; set; }
    public int? RestrikeStartMintDate { get; set; }
    public int? RestrikeEndMintDate { get; set; }

    public ICollection<CoinTypesIssuersRulersRel> IssuerRulerRelations { get; set; } = new List<CoinTypesIssuersRulersRel>();
    public ICollection<CoinTypeSample> Samples { get; set; } = new List<CoinTypeSample>();
}
