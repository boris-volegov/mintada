using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Mintada.Navigator.Models
{
    public class Issuer
    {
        public long Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string UrlSlug { get; set; } = string.Empty;
        public string? ParentUrlSlug { get; set; }
        public string TerritoryType { get; set; } = string.Empty;
        
        [JsonIgnore]
        public List<Issuer> Children { get; set; } = new List<Issuer>();

        public bool HasNonReferenceSamples { get; set; }


        public override string ToString() => Name;
    }
}
