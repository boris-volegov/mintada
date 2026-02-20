import { useEffect, useState, type CSSProperties, type KeyboardEvent } from 'react';
import { Link, useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { IssuersService, type IssuerDto, type CoinTypeDto } from '../../api';
import { IssuerTreeService } from '../../services/IssuerTreeService';
import type { IssuerTreeDto } from '../../models/IssuerTreeDto';
import type { CatalogIssuerRulerNodeDto } from '../../models/CatalogIssuerRulerNodeDto';
import { CatalogBrowseService } from '../../services/CatalogBrowseService';
import { IssuerNode } from './IssuerNode';
import { useIssuerFilter } from './useIssuerFilter';
import { useAlphabeticalGrouping } from './useAlphabeticalGrouping';
import { CoinList } from './CoinList';
import { DefaultIssuerLayout } from './DefaultIssuerLayout';
import { RulerCatalogPanel } from './RulerCatalogPanel';
import { ScrollToTop } from '../ScrollToTop/ScrollToTop';
import type { IssuerTreeViewNode } from './issuerTreeView.types';
import issuerViewIcon from '../../assets/images/catalog-view-issuer.svg';
import rulerViewIcon from '../../assets/images/catalog-view-ruler.svg';
import shapeViewIcon from '../../assets/images/catalog-view-shape.svg';
import './IssuerBrowser.css';

type CatalogBrowseMode = 'issuer' | 'ruler' | 'shape';

type CatalogBrowseModeOption = {
  mode: CatalogBrowseMode;
  label: string;
  iconUrl: string;
};

const catalogBrowseModeOptions: CatalogBrowseModeOption[] = [
  { mode: 'issuer', label: 'Issuer', iconUrl: issuerViewIcon },
  { mode: 'ruler', label: 'Ruler', iconUrl: rulerViewIcon },
  { mode: 'shape', label: 'Shape', iconUrl: shapeViewIcon },
];
const catalogBrowseModes: CatalogBrowseMode[] = ['issuer', 'ruler', 'shape'];

function parseCatalogBrowseMode(rawValue: string | null): CatalogBrowseMode {
  if (rawValue === 'ruler' || rawValue === 'shape') {
    return rawValue;
  }

  return 'issuer';
}

export function IssuerBrowser() {
  const { issuerSlug } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [roots, setRoots] = useState<IssuerTreeDto[]>([]);
  const [rulerRoots, setRulerRoots] = useState<CatalogIssuerRulerNodeDto[]>([]);
  const [rulerLoading, setRulerLoading] = useState(false);
  const [rulerLoadError, setRulerLoadError] = useState<string | null>(null);
  const [selectedIssuer, setSelectedIssuer] = useState<IssuerDto | null>(null);
  const [coinTypes, setCoinTypes] = useState<CoinTypeDto[]>([]);
  const [loading, setLoading] = useState(false);
  const browseMode = parseCatalogBrowseMode(searchParams.get('view'));

  // Filter State
  const [filterText, setFilterText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortOption, setSortOption] = useState(() => {
    return localStorage.getItem('issuerSortOption') || 'default';
  });

  // Filter Logic
  const filteredRoots = useIssuerFilter(roots, filterText);

  // Persist Sort Option
  useEffect(() => {
    localStorage.setItem('issuerSortOption', sortOption);
  }, [sortOption]);

  // Alphabetical Grouping Logic (Memoized)
  const isAlphabetical = sortOption === 'alphabetical';
  const alphabeticalData = useAlphabeticalGrouping(filteredRoots, isAlphabetical);


  useEffect(() => {
    // Initial Load of Hierarchy
    setLoading(true);
    IssuerTreeService.getIssuerHierarchy()
      .then(data => {
        setRoots(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (browseMode !== 'ruler') {
      return;
    }

    if (rulerRoots.length > 0 || rulerLoading) {
      return;
    }

    setRulerLoading(true);
    setRulerLoadError(null);

    CatalogBrowseService.getRulerBrowser()
      .then((data) => {
        setRulerRoots(data);
        setRulerLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setRulerLoadError('Could not load ruler catalog. Please try again.');
        setRulerLoading(false);
      });
  }, [browseMode, rulerLoading, rulerRoots.length]);

  // Sync URL to Selected Issuer
  useEffect(() => {
    if (!issuerSlug) {
      setSelectedIssuer(null);
      setCoinTypes([]);
      return;
    }

    if (roots.length === 0) return; // Wait for data

    const findIssuerBySlug = (nodes: IssuerTreeDto[], slug: string): IssuerDto | null => {
      for (const node of nodes) {
        if (node.urlSlug === slug) return node;
        if (node.children) {
          const found = findIssuerBySlug(node.children, slug);
          if (found) return found;
        }
      }
      return null;
    };

    const issuer = findIssuerBySlug(roots, issuerSlug);
    if (issuer) {
      setSelectedIssuer(issuer);
      // Fetch coins for this issuer
      const issuerId = typeof issuer.id === 'string' ? Number(issuer.id) : issuer.id;
      if (issuerId == null || Number.isNaN(issuerId)) {
        console.warn(`Issuer ${issuerSlug} has an invalid id and coin types cannot be loaded.`);
        setCoinTypes([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      IssuersService.getApiIssuersCoinTypes(issuerId)
        .then(data => {
          setCoinTypes(data);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });
    } else {
      // Slug not found in loaded tree?
      // Maybe handle 404 or just ignore
      console.warn(`Issuer with slug ${issuerSlug} not found in current hierarchy.`);
    }

  }, [issuerSlug, roots]);


  const handleIssuerSelect = (issuer: IssuerTreeViewNode) => {
    if (issuer.urlSlug) {
      navigate(`/catalog/issuers/${issuer.urlSlug}`);
    }
  };

  const handleBrowseModeChange = (mode: CatalogBrowseMode) => {
    if (mode === browseMode) {
      return;
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('view', mode);
    setSearchParams(nextParams, { replace: true });
  };

  const handleBrowseModeKeyDown = (event: KeyboardEvent<HTMLButtonElement>, currentMode: CatalogBrowseMode) => {
    const currentIndex = catalogBrowseModes.indexOf(currentMode);
    if (currentIndex === -1) {
      return;
    }

    let nextIndex = currentIndex;
    if (event.key === 'ArrowRight') {
      nextIndex = (currentIndex + 1) % catalogBrowseModes.length;
    } else if (event.key === 'ArrowLeft') {
      nextIndex = (currentIndex - 1 + catalogBrowseModes.length) % catalogBrowseModes.length;
    } else if (event.key === 'Home') {
      nextIndex = 0;
    } else if (event.key === 'End') {
      nextIndex = catalogBrowseModes.length - 1;
    } else {
      return;
    }

    event.preventDefault();
    const nextMode = catalogBrowseModes[nextIndex];
    handleBrowseModeChange(nextMode);
    document.getElementById(`catalog-browse-tab-${nextMode}`)?.focus();
  };

  if (loading && roots.length === 0) return <div className="loading-state">Loading Mintada Catalog...</div>;

  return (
    <div className="issuer-browser" style={{
      minHeight: '100vh',
      width: '100%'
    }}>
      <div className="breadcrumb-stripe-container">
        <div className="breadcrumb-bg-layer">
          <div className="breadcrumb-bg-solid"></div>
          <div className="breadcrumb-bg-gradient"></div>
        </div>
        <div className="breadcrumb-content">
          <Link to="/" className="breadcrumb-link">Home</Link>
          <span className="breadcrumb-separator">&rsaquo;</span>
          {selectedIssuer ? (
            <>
              <Link to="/catalog/issuers" className="breadcrumb-link">Catalog</Link>
              <span className="breadcrumb-separator">&rsaquo;</span>
              <span className="breadcrumb-inactive">{selectedIssuer.name}</span>
            </>
          ) : (
            <span className="breadcrumb-inactive">Catalog</span>
          )}
        </div>
      </div>

      {selectedIssuer ? (
        <div className="issuer-list-container fade-in">
          <div className="issuer-tree-container glass-panel">
            <h2 className="section-title">
              {selectedIssuer.name} <span style={{ fontSize: '1rem', color: '#999', fontWeight: 'normal' }}>({selectedIssuer.territoryType})</span>
            </h2>
            <div className="title-separator-gradient"></div>

            <CoinList
              coinTypes={coinTypes}
              selectedIssuer={selectedIssuer}
              loading={loading}
            />
          </div>
        </div>
      ) : (
        <div className="issuer-list-container fade-in">
          <div className="issuer-tree-container glass-panel">
            <div className="issuer-list-header">
              <h2 className="section-title">Catalog of World Coins</h2>
              <div className="title-separator-gradient"></div>

              <div className="catalog-browse-row">
                <span className="catalog-browse-label">View by:</span>
                <div className="catalog-browse-scroll">
                  <div className="catalog-browse-tabs" role="tablist" aria-label="Catalog browse mode">
                    {catalogBrowseModeOptions.map((option) => {
                      const isActive = browseMode === option.mode;
                      return (
                        <button
                          key={option.mode}
                          id={`catalog-browse-tab-${option.mode}`}
                          role="tab"
                          aria-selected={isActive}
                          aria-controls={`catalog-browse-panel-${option.mode}`}
                          tabIndex={isActive ? 0 : -1}
                          className={`catalog-browse-tab ${isActive ? 'active' : ''}`}
                          data-mode={option.mode}
                          onClick={() => handleBrowseModeChange(option.mode)}
                          onKeyDown={(event) => handleBrowseModeKeyDown(event, option.mode)}
                          style={{ '--catalog-browse-icon': `url("${option.iconUrl}")` } as CSSProperties}
                        >
                          <span className="catalog-browse-icon" aria-hidden="true"></span>
                          <span>{option.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
              <div className="title-separator-gradient"></div>

              <div
                id="catalog-browse-panel-issuer"
                role="tabpanel"
                aria-labelledby="catalog-browse-tab-issuer"
                className="catalog-browse-panel"
                hidden={browseMode !== 'issuer'}
              >
                {browseMode === 'issuer' && (
                  <>
                    {/* Filter Toolbar */}
                    <div className="issuer-filter-toolbar">
                      <div className="filter-row">
                        <div className="filter-left-group">
                          <div className="filter-group">
                            <label className="filter-label">Filter:</label>
                            <input
                              type="text"
                              className="filter-input"
                              value={filterText}
                              onChange={(e) => setFilterText(e.target.value)}
                            />
                          </div>
                          <div className="filter-group">
                            <label className="filter-label">Category:</label>
                            <select
                              className="filter-select"
                              value={categoryFilter}
                              onChange={(e) => setCategoryFilter(e.target.value)}
                            >
                              <option value="">Category</option>
                              {/* Placeholder options */}
                              <option value="historical">Historical</option>
                              <option value="existing">Existing</option>
                            </select>
                          </div>
                          <button className="clear-button" onClick={() => {
                            setFilterText('');
                            setCategoryFilter('');
                            // Do NOT reset sortOption
                          }}>
                            Clear
                          </button>
                        </div>

                        <div className="filter-right-group">
                          <div className="filter-group">
                            <label className="filter-label">Sort:</label>
                            <select
                              className="filter-select"
                              value={sortOption}
                              onChange={(e) => setSortOption(e.target.value)}
                            >
                              <option value="default">Default</option>
                              <option value="alphabetical">Alphabetically</option>
                            </select>
                          </div>
                        </div>
                      </div>
                      <div className="toolbar-separator-gradient"></div>
                    </div>

                    {/* Letter Selector for Alphabetical Mode */}
                    {sortOption === 'alphabetical' && (
                      <div className="letter-selector fade-in">
                        {Array.from('ABCDEFGHIJKLMNOPQRSTUVWXYZ').map((letter, index) => (
                          <span key={letter} className="letter-link">
                            {index > 0 && <span className="letter-separator">&middot;</span>}
                            <a
                              href={`#section-${letter}`}
                              onClick={(e) => {
                                e.preventDefault();
                                const element = document.getElementById(`section-${letter}`);
                                if (element) {
                                  element.scrollIntoView({ behavior: 'auto', block: 'start' });
                                }
                              }}
                            >
                              {letter}
                            </a>
                          </span>
                        ))}
                      </div>
                    )}

                    {(() => {
                      // Determine layout mode
                      if (sortOption === 'alphabetical' && alphabeticalData) {
                        const { sortedKeys, grouped } = alphabeticalData;

                        return (
                          <div className="issuer-alphabetical-container">
                            {sortedKeys.map(key => (
                              <div key={key} id={`section-${key}`} className="issuer-section">
                                <h3 className="issuer-section-header">{key}</h3>
                                <div className="issuer-grid">
                                  {(grouped.get(key) || []).map(node => (
                                    <IssuerNode
                                      key={node.id}
                                      node={node}
                                      onSelect={(n) => {
                                        if (n.urlSlug) {
                                          navigate(`/catalog/issuers/${n.urlSlug}`);
                                        }
                                      }}
                                      level={node.isTopLevelLeaf ? 0 : 1} // Bold if top-level, normal otherwise
                                      showFlag={!!node.isTopLevelLeaf}
                                      disableIndent={true}
                                    />
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        );
                      }

                      return (
                        <DefaultIssuerLayout
                          filteredRoots={filteredRoots}
                          onSelect={handleIssuerSelect}
                        />
                      );
                    })()}
                  </>
                )}
              </div>

              <div
                id="catalog-browse-panel-ruler"
                role="tabpanel"
                aria-labelledby="catalog-browse-tab-ruler"
                className="catalog-browse-panel"
                hidden={browseMode !== 'ruler'}
              >
                {browseMode === 'ruler' && (
                  <RulerCatalogPanel
                    roots={rulerRoots}
                    loading={rulerLoading}
                    error={rulerLoadError}
                  />
                )}
              </div>

              <div
                id="catalog-browse-panel-shape"
                role="tabpanel"
                aria-labelledby="catalog-browse-tab-shape"
                className="catalog-browse-placeholder"
                hidden={browseMode !== 'shape'}
              >
                <h3>Shape Catalog View</h3>
                <p>This view is ready in the UI and will display grouped shape data as soon as the API endpoint is added.</p>
              </div>
            </div>

            {browseMode === 'issuer' && filteredRoots.length === 0 && <div className="empty-state">No issuers found.</div>}
          </div>
        </div>
      )}
      <ScrollToTop />
    </div>
  );
}
