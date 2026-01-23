namespace Mintada.Api.Dtos;

public class CoinTypeDetailDto : CoinTypeDto
{
    public IEnumerable<CoinTypeSampleDto> Samples { get; set; } = new List<CoinTypeSampleDto>();
}
