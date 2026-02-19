using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("issuer_types")]
public class IssuerType : BaseEntity
{
    public string Name { get; set; } = null!;
}
