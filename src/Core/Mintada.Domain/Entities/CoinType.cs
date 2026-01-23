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
    public string? Period { get; set; }
    public int? RarityIndex { get; set; }
    public string CoinTypeSlug { get; set; } = null!;
    public DateTime DateTimeInserted { get; set; }
    public int IssueTypeId { get; set; }
    
    public ICollection<CoinTypeSample> Samples { get; set; } = new List<CoinTypeSample>();
}
