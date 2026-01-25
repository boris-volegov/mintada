namespace Mintada.Navigator.Models
{
    public class CoinShape
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public int? SeqNumber { get; set; }

        public override string ToString()
        {
            return Name;
        }
    }
}
