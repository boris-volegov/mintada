using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("issuers_rulers_rel")]
public class IssuersRulersRel : BaseEntity
{
    public int IssuerId { get; set; }
    public Issuer Issuer { get; set; } = null!;

    public int? GroupId { get; set; }
    public IssuersRulersRelGroup? Group { get; set; }

    public int RulerId { get; set; }
    public Ruler Ruler { get; set; } = null!;

    public string? Name { get; set; }
    public string? RuleType { get; set; }
    public int? StartYear { get; set; }
    public int? EndYear { get; set; }
    public bool IsApprox { get; set; }

    public ICollection<CoinTypesIssuersRulersRel> CoinTypeRelations { get; set; } = new List<CoinTypesIssuersRulersRel>();
}
