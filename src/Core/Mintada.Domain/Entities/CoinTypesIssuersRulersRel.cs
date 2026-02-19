using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("coin_types_issuers_rulers_rel")]
public class CoinTypesIssuersRulersRel
{
    public int CoinTypeId { get; set; }
    public CoinType CoinType { get; set; } = null!;

    public int IssuerRulerRelId { get; set; }
    public IssuersRulersRel IssuerRulerRel { get; set; } = null!;
}
