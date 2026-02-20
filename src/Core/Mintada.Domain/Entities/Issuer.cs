using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("issuers")]
public class Issuer : BaseEntity
{
    public int? ParentId { get; set; }
    public Issuer? Parent { get; set; }
    public int? IssuerTypeId { get; set; }
    public IssuerType? IssuerType { get; set; }
    
    public string? Name { get; set; }
    public string? UrlSlug { get; set; }
    public string? TerritoryType { get; set; }
    public bool IsHistoricalPeriod { get; set; }
    public bool IsSection { get; set; }
    public bool IsRulersContainer { get; set; }

    public ICollection<IssuerAltName> AltNames { get; set; } = new List<IssuerAltName>();
    public ICollection<CoinType> CoinTypes { get; set; } = new List<CoinType>();
    public ICollection<Issuer> Children { get; set; } = new List<Issuer>();
}
