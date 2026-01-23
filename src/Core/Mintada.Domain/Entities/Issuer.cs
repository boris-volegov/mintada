using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("issuers")]
public class Issuer : BaseEntity
{
    public int? ParentId { get; set; }
    public Issuer? Parent { get; set; }
    public int? TopParentId { get; set; }
    public Issuer? TopParent { get; set; }
    
    public string? Url { get; set; }
    public string? Name { get; set; }
    public string? UrlSlug { get; set; }
    public string? ParentUrlSlug { get; set; }
    public string? AltNames { get; set; }
    public string? TerritoryType { get; set; }
    public bool IsHistoricalPeriod { get; set; }
    public bool IsSection { get; set; }
    
    public string? NumistaName { get; set; }
    public string? NumistaTerritoryType { get; set; }
    public string? NumistaUrlSlug { get; set; }
    public string? NumistaParentUrlSlug { get; set; }

    public ICollection<CoinType> CoinTypes { get; set; } = new List<CoinType>();
    public ICollection<Issuer> Children { get; set; } = new List<Issuer>();
}
