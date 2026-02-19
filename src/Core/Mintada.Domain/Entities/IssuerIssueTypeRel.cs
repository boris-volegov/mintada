using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("issuers_issue_types_rel")]
public class IssuerIssueTypeRel
{
    public int IssuerId { get; set; }
    public Issuer Issuer { get; set; } = null!;

    public int IssueTypeId { get; set; }
    public IssueType IssueType { get; set; } = null!;

    public ICollection<CoinType> CoinTypes { get; set; } = new List<CoinType>();
}
