import { useEffect, useMemo, useState, type SyntheticEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { OpenAPI } from '../../api';
import noSampleImage from '../../assets/images/no_sample_image.svg';
import type { RulerCoinTypeItemDto } from '../../models/RulerCoinTypeItemDto';
import type { RulerIssuerCoinTypeGroupDto } from '../../models/RulerIssuerCoinTypeGroupDto';
import type { RulerCoinTypesResponseDto } from '../../models/RulerCoinTypesResponseDto';
import { RulerBrowseService } from '../../services/RulerBrowseService';
import './CoinList.css';
import './IssuerBrowser.css';

function buildImageUrl(
  issuerSlug: string | null | undefined,
  coinTypeSlug: string | null | undefined,
  coinTypeId: number | undefined,
  fileName: string | null | undefined,
): string {
  if (!issuerSlug || !coinTypeSlug || !coinTypeId || !fileName) {
    return noSampleImage;
  }

  return `${OpenAPI.BASE}/images/coin_samples/${issuerSlug}/${coinTypeSlug}_${coinTypeId}/images/${fileName}`;
}

function sanitizeRulerInfoHtml(rawHtml: string | null | undefined): string {
  if (!rawHtml) {
    return '';
  }

  return rawHtml
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/\son\w+="[^"]*"/gi, '')
    .replace(/\son\w+='[^']*'/gi, '')
    .replace(/javascript:/gi, '');
}

function RulerCoinRows({
  issuerGroup,
  coinTypes,
}: {
  issuerGroup: RulerIssuerCoinTypeGroupDto;
  coinTypes: RulerCoinTypeItemDto[];
}) {
  const handleImageError = (event: SyntheticEvent<HTMLImageElement>) => {
    event.currentTarget.src = noSampleImage;
    event.currentTarget.style.opacity = '0.5';
  };

  return (
    <div className="coin-list">
      {coinTypes.map((coin) => (
        <div key={`${issuerGroup.issuerId}-${coin.id}`} className="coin-list-item">
          <div className="coin-list-images">
            <div className="coin-list-image-wrapper">
              <img
                src={buildImageUrl(
                  issuerGroup.issuerUrlSlug,
                  coin.coinTypeSlug,
                  coin.id,
                  coin.obverseImage,
                )}
                alt={coin.obverseImage ? `${coin.title} obverse` : 'No obverse image'}
                loading="lazy"
                onError={handleImageError}
              />
            </div>
            <div className="coin-list-image-wrapper">
              <img
                src={buildImageUrl(
                  issuerGroup.issuerUrlSlug,
                  coin.coinTypeSlug,
                  coin.id,
                  coin.reverseImage,
                )}
                alt={coin.reverseImage ? `${coin.title} reverse` : 'No reverse image'}
                loading="lazy"
                onError={handleImageError}
              />
            </div>
          </div>

          <div className="coin-list-info">
            <div className="coin-list-title">{coin.title}</div>
            <div className="coin-list-meta">
              {coin.subtitle ? <span>{coin.subtitle}</span> : null}
              {coin.period ? <span className="badge">{coin.period}</span> : null}
              {coin.rarityIndex != null ? <span>Rarity: {coin.rarityIndex}</span> : null}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function RulerDetailPage() {
  const { rulerId } = useParams<{ rulerId: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RulerCoinTypesResponseDto | null>(null);

  const numericRulerId = useMemo(() => {
    if (!rulerId) {
      return null;
    }
    const parsed = Number(rulerId);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  }, [rulerId]);

  const safeInfoHtml = useMemo(
    () => sanitizeRulerInfoHtml(response?.infoHtml),
    [response?.infoHtml],
  );

  useEffect(() => {
    if (!numericRulerId) {
      setLoading(false);
      setError('Invalid ruler id.');
      return;
    }

    setLoading(true);
    setError(null);

    RulerBrowseService.getRulerCoinTypes(numericRulerId)
      .then((data) => {
        setResponse(data);
        setLoading(false);
      })
      .catch((requestError) => {
        console.error(requestError);
        setError('Could not load ruler catalog details.');
        setLoading(false);
      });
  }, [numericRulerId]);

  return (
    <div className="issuer-browser">
      <div className="breadcrumb-stripe-container">
        <div className="breadcrumb-bg-layer">
          <div className="breadcrumb-bg-solid"></div>
          <div className="breadcrumb-bg-gradient"></div>
        </div>
        <div className="breadcrumb-content">
          <Link to="/" className="breadcrumb-link">Home</Link>
          <span className="breadcrumb-separator">&rsaquo;</span>
          <Link to="/catalog/issuers?view=ruler" className="breadcrumb-link">Ruler Catalog</Link>
          {response?.rulerName ? (
            <>
              <span className="breadcrumb-separator">&rsaquo;</span>
              <span className="breadcrumb-inactive">{response.rulerName}</span>
            </>
          ) : null}
        </div>
      </div>

      <div className="issuer-list-container fade-in">
        <div className="issuer-tree-container glass-panel">
          {loading ? <div className="loading-state">Loading ruler details...</div> : null}
          {error ? <div className="empty-state">{error}</div> : null}

          {!loading && !error && response ? (
            <>
              <h2 className="section-title">
                {response.rulerName}
                <span className="section-title-meta">
                  {' '}
                  ({response.issuerGroups.reduce((sum, group) => sum + group.coinTypes.length, 0)} coin types)
                </span>
              </h2>
              <div className="title-separator-gradient brand-divider"></div>

              {(response.portraitUrl || safeInfoHtml) ? (
                <section className="ruler-detail-hero">
                  {response.portraitUrl ? (
                    <div className="ruler-detail-portrait-wrap">
                      <img
                        src={response.portraitUrl}
                        alt={`${response.rulerName} portrait`}
                        className="ruler-detail-portrait"
                        loading="lazy"
                      />
                    </div>
                  ) : null}

                  {safeInfoHtml ? (
                    <article
                      className="ruler-detail-info"
                      dangerouslySetInnerHTML={{ __html: safeInfoHtml }}
                    />
                  ) : null}
                </section>
              ) : null}

              {response.issuerGroups.length === 0 ? (
                <div className="empty-state">No coin types linked to this ruler.</div>
              ) : null}

              {response.issuerGroups.map((issuerGroup) => (
                <section key={issuerGroup.issuerId}>
                  {response.hasMultipleIssuers ? (
                    <h3 className="issuer-section-header">
                      {issuerGroup.issuerName ?? `Issuer ${issuerGroup.issuerId}`}
                    </h3>
                  ) : null}
                  <RulerCoinRows issuerGroup={issuerGroup} coinTypes={issuerGroup.coinTypes} />
                </section>
              ))}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
