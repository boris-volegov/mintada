using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("issuers_rulers_rel_groups")]
public class IssuersRulersRelGroup : BaseEntity
{
    public int IssuerId { get; set; }
    public Issuer Issuer { get; set; } = null!;

    public string Name { get; set; } = null!;

    public ICollection<IssuersRulersRel> RulerRelations { get; set; } = new List<IssuersRulersRel>();
}
