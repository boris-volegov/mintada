using System.ComponentModel.DataAnnotations.Schema;

namespace Mintada.Domain.Entities;

[Table("issuer_alt_names")]
public class IssuerAltName
{
    public int IssuerId { get; set; }
    public Issuer Issuer { get; set; } = null!;

    public string AltName { get; set; } = null!;
}
