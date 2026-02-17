import type { SyntheticEvent } from 'react';
import { OpenAPI, type CoinTypeDto, type IssuerDto } from '../../api';
import noSampleImage from '../../assets/images/no_sample_image.svg';
import './CoinList.css';

interface CoinListProps {
    coinTypes: CoinTypeDto[];
    selectedIssuer: IssuerDto;
    loading: boolean;
}

export function CoinList({ coinTypes, selectedIssuer, loading }: CoinListProps) {

    const getImageUrl = (issuerSlug: string | null | undefined, coinTypeSlug: string | null | undefined, coinId: number | undefined, filename: string | null | undefined) => {
        if (!filename || !issuerSlug || !coinTypeSlug || coinId == null) return undefined;
        return `${OpenAPI.BASE}/images/coin_samples/${issuerSlug}/${coinTypeSlug}_${coinId}/images/${filename}`;
    };

    const getCoinImageSrc = (coin: CoinTypeDto, imageName: string | null | undefined) => {
        return getImageUrl(selectedIssuer.urlSlug, coin.coinTypeSlug, coin.id, imageName) ?? noSampleImage;
    };

    const handleImageError = (e: SyntheticEvent<HTMLImageElement>) => {
        e.currentTarget.src = noSampleImage;
        e.currentTarget.style.opacity = '0.5';
    };

    return (
        <div className="coin-list">
            {coinTypes.map(coin => (
                <div key={coin.id} className="coin-list-item">
                    {/* Images Column */}
                    <div className="coin-list-images">
                        <div className="coin-list-image-wrapper">
                            <img
                                src={getCoinImageSrc(coin, coin.obverseImage)}
                                alt={coin.obverseImage ? `${coin.title} Obverse` : "No Obverse Image"}
                                loading="lazy"
                                onError={handleImageError}
                            />
                        </div>
                        <div className="coin-list-image-wrapper">
                            <img
                                src={getCoinImageSrc(coin, coin.reverseImage)}
                                alt={coin.reverseImage ? `${coin.title} Reverse` : "No Reverse Image"}
                                loading="lazy"
                                onError={handleImageError}
                            />
                        </div>
                    </div>

                    {/* Info Column */}
                    <div className="coin-list-info">
                        <div className="coin-list-title">{coin.title}</div>
                        <div className="coin-list-meta">
                            {coin.period && <span className="badge">{coin.period}</span>}
                            {coin.rarityIndex != null && <span>Rarity: {coin.rarityIndex}</span>}
                        </div>
                    </div>
                </div>
            ))}
            {coinTypes.length === 0 && !loading && (
                <div className="empty-state">No coin types found for {selectedIssuer.name}.</div>
            )}
        </div>
    );
}
