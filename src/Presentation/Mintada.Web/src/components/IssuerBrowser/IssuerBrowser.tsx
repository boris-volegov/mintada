import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { IssuersService, type IssuerDto, type CoinTypeDto } from '../../api';
import { IssuerTreeService } from '../../services/IssuerTreeService';
import type { IssuerTreeDto } from '../../models/IssuerTreeDto';
import { IssuerNode } from './IssuerNode';
import { useIssuerFilter } from './useIssuerFilter';
import { useAlphabeticalGrouping } from './useAlphabeticalGrouping';
import { CoinList } from './CoinList';
import { DefaultIssuerLayout } from './DefaultIssuerLayout';
import { ScrollToTop } from '../ScrollToTop/ScrollToTop';
import './IssuerBrowser.css';

export function IssuerBrowser() {
  const { issuerSlug } = useParams();
  const navigate = useNavigate();
  const [roots, setRoots] = useState<IssuerTreeDto[]>([]);
  const [selectedIssuer, setSelectedIssuer] = useState<IssuerDto | null>(null);
  const [coinTypes, setCoinTypes] = useState<CoinTypeDto[]>([]);
  const [loading, setLoading] = useState(false);

  // Filter State
  const [filterText, setFilterText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sortOption, setSortOption] = useState(() => {
    return localStorage.getItem('issuerSortOption') || 'default';
  });

  // Filter Logic
  const filteredRoots = useIssuerFilter(roots, filterText, sortOption);

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
      setLoading(true);
      IssuersService.getApiIssuersCoinTypes(issuer.id as number)
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


  const handleIssuerSelect = (issuer: IssuerDto) => {
    if (issuer.urlSlug) {
      navigate(`/catalog/issuers/${issuer.urlSlug}`);
    }
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
          <span className="breadcrumb-separator">›</span>
          {selectedIssuer ? (
            <>
              <Link to="/catalog/issuers" className="breadcrumb-link">Catalog</Link>
              <span className="breadcrumb-separator">›</span>
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
                        onChange={(e) => {
                          const val = e.target.value;
                          setLoading(true);
                          // Small timeout to allow UI to render the loading state
                          setTimeout(() => {
                            setSortOption(val);
                            setLoading(false);
                          }, 50);
                        }}
                      >
                        <option value="default">Default</option>
                        <option value="alphabetical">Alphabetically</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div className="toolbar-separator-gradient"></div>
              </div>
            </div>

            {/* Letter Selector for Alphabetical Mode */}
            {sortOption === 'alphabetical' && (
              <div className="letter-selector fade-in">
                {Array.from("ABCDEFGHIJKLMNOPQRSTUVWXYZ").map((letter, index) => (
                  <span key={letter} className="letter-link">
                    {index > 0 && <span className="letter-separator">·</span>}
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
                              level={(node as any)._isTopLevel ? 0 : 1} // Bold if top-level, normal otherwise
                              showFlag={!!(node as any)._isTopLevel}
                              disableIndent={true}
                            />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                );
              } else {
                return (
                  <DefaultIssuerLayout
                    filteredRoots={filteredRoots}
                    onSelect={handleIssuerSelect}
                  />
                );
              }
            })()}

            {filteredRoots.length === 0 && <div className="empty-state">No issuers found.</div>}
          </div>
        </div >
      )
      }
      <ScrollToTop />
    </div >
  );
}
