import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { CatalogIssuerRulerNodeDto } from '../../models/CatalogIssuerRulerNodeDto';

interface RulerCatalogPanelProps {
  roots: CatalogIssuerRulerNodeDto[];
  loading: boolean;
  error: string | null;
}

function normalize(text: string | null | undefined): string {
  return (text ?? '').toLowerCase();
}

function groupRulersForDisplay(rulers: CatalogIssuerRulerNodeDto['rulers']) {
  const grouped = new Map<string, CatalogIssuerRulerNodeDto['rulers']>();
  const ungrouped: CatalogIssuerRulerNodeDto['rulers'] = [];

  for (const ruler of rulers) {
    const groupName = ruler.groupName?.trim();
    if (!groupName) {
      ungrouped.push(ruler);
      continue;
    }

    const existingGroup = grouped.get(groupName);
    if (existingGroup) {
      existingGroup.push(ruler);
    } else {
      grouped.set(groupName, [ruler]);
    }
  }

  const groups = [...grouped.entries()]
    .sort(([left], [right]) => left.localeCompare(right, undefined, { sensitivity: 'base' }))
    .map(([groupName, groupRulers]) => ({ groupName, rulers: groupRulers }));

  return { ungrouped, groups };
}

function filterRulerTree(
  nodes: CatalogIssuerRulerNodeDto[],
  query: string,
): CatalogIssuerRulerNodeDto[] {
  if (!query) {
    return nodes;
  }

  const filterNode = (node: CatalogIssuerRulerNodeDto): CatalogIssuerRulerNodeDto | null => {
    const childMatches = node.children
      .map(filterNode)
      .filter((child): child is CatalogIssuerRulerNodeDto => child !== null);

    const matchingRulers = node.rulers.filter((ruler) =>
      normalize(ruler.name).includes(query) ||
      normalize(ruler.groupName).includes(query) ||
      normalize(ruler.ruleType).includes(query) ||
      normalize(ruler.title).includes(query),
    );

    const issuerMatch =
      normalize(node.name).includes(query) ||
      normalize(node.urlSlug).includes(query) ||
      normalize(node.territoryType).includes(query);

    if (!issuerMatch && childMatches.length === 0 && matchingRulers.length === 0) {
      return null;
    }

    return {
      ...node,
      children: childMatches,
      rulers: matchingRulers,
    };
  };

  return nodes
    .map(filterNode)
    .filter((node): node is CatalogIssuerRulerNodeDto => node !== null);
}

function getRootLetter(name: string | null | undefined): string {
  const candidate = (name ?? '').trim().charAt(0).toUpperCase();
  return /[A-Z]/.test(candidate) ? candidate : '#';
}

interface RulerTreeNodeProps {
  node: CatalogIssuerRulerNodeDto;
  level: number;
  forceExpanded: boolean;
}

function RulerTreeNode({ node, level, forceExpanded }: RulerTreeNodeProps) {
  const hasChildren = node.children.length > 0;
  const hasRulers = node.rulers.length > 0;
  const canExpand = hasChildren || hasRulers;
  const isRoot = level === 0;
  const initialExpanded = isRoot && hasChildren;
  const [isExpandedState, setIsExpandedState] = useState(initialExpanded);
  const [hasUserExpandedRoot, setHasUserExpandedRoot] = useState(false);

  useEffect(() => {
    if (forceExpanded) {
      setIsExpandedState(true);
    }
  }, [forceExpanded]);

  const expanded = forceExpanded || isExpandedState;
  const showRulers = hasRulers && (!isRoot || !hasChildren || hasUserExpandedRoot || forceExpanded);
  const rowIndent = level === 0 ? 0 : 20;
  const { ungrouped, groups } = useMemo(() => groupRulersForDisplay(node.rulers), [node.rulers]);

  const handleToggle = () => {
    setIsExpandedState((previous) => {
      const next = !previous;
      if (isRoot && next) {
        setHasUserExpandedRoot(true);
      }

      return next;
    });
  };

  return (
    <div className="ruler-node">
      <div className="ruler-node-row catalog-tree-row catalog-tree-row--item" style={{ paddingLeft: `${rowIndent}px` }}>
        {canExpand ? (
          <button
            type="button"
            className={`ruler-toggle catalog-tree-toggle ${expanded ? 'expanded' : ''}`}
            onClick={handleToggle}
            aria-label={expanded ? 'Collapse node' : 'Expand node'}
          >
            {'\u25B6'}
          </button>
        ) : (
          <span className="ruler-toggle-spacer catalog-tree-toggle-spacer" aria-hidden="true"></span>
        )}

        <div className="ruler-node-title catalog-tree-label">
          {(isRoot || !node.parentId) && node.urlSlug ? (
            <span
              className={`sprite s${node.urlSlug} ruler-node-flag`}
              aria-hidden="true"
            ></span>
          ) : null}
          <span className={`ruler-node-name catalog-tree-name ${isRoot ? 'catalog-tree-name--root' : ''}`}>
            {node.name ?? 'Unnamed issuer'}
          </span>
          {node.isHistoricalPeriod ? <span className="ruler-node-tag">Historical</span> : null}
        </div>
      </div>

      {expanded ? (
        <div className="ruler-node-details">
          {showRulers ? (
            <div className="ruler-groups">
              {ungrouped.length > 0 ? (
                <ul className="ruler-list">
                  {ungrouped.map((ruler, index) => (
                    <li key={`ungrouped-${ruler.id}-${ruler.ruleType ?? ''}-${index}`} className="ruler-list-item catalog-chip">
                      <Link to={`/catalog/rulers/${ruler.id}`} className="catalog-link catalog-tree-name catalog-chip-link">
                        {ruler.name}
                      </Link>
                      {ruler.ruleType ? <span className="ruler-meta catalog-tree-meta catalog-chip-meta">{ruler.ruleType}</span> : null}
                      {ruler.title ? <span className="ruler-meta catalog-tree-meta catalog-chip-meta">{ruler.title}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : null}

              {groups.map((group, groupIndex) => (
                <div key={`${group.groupName}-${groupIndex}`} className="ruler-group">
                  <div className="ruler-group-name">{group.groupName}</div>
                  <ul className="ruler-list">
                    {group.rulers.map((ruler, index) => (
                      <li
                        key={`${group.groupName}-${ruler.id}-${ruler.ruleType ?? ''}-${index}`}
                        className="ruler-list-item catalog-chip"
                      >
                        <Link to={`/catalog/rulers/${ruler.id}`} className="catalog-link catalog-tree-name catalog-chip-link">
                          {ruler.name}
                        </Link>
                        {ruler.ruleType ? <span className="ruler-meta catalog-tree-meta catalog-chip-meta">{ruler.ruleType}</span> : null}
                        {ruler.title ? <span className="ruler-meta catalog-tree-meta catalog-chip-meta">{ruler.title}</span> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          ) : null}

          {hasChildren ? (
            <div className="ruler-children">
              {node.children.map((child, index) => (
                <RulerTreeNode
                  key={`${child.id ?? child.urlSlug ?? child.name ?? 'issuer'}-${index}`}
                  node={child}
                  level={level + 1}
                  forceExpanded={forceExpanded}
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function RulerCatalogPanel({ roots, loading, error }: RulerCatalogPanelProps) {
  const [searchText, setSearchText] = useState('');

  const normalizedQuery = useMemo(() => normalize(searchText.trim()), [searchText]);
  const filteredRoots = useMemo(
    () => filterRulerTree(roots, normalizedQuery),
    [roots, normalizedQuery],
  );
  const sortedRoots = useMemo(
    () => [...filteredRoots].sort((left, right) => (left.name ?? '').localeCompare(right.name ?? '', undefined, { sensitivity: 'base' })),
    [filteredRoots],
  );
  const groupedRootsByLetter = useMemo(() => {
    const grouped = new Map<string, CatalogIssuerRulerNodeDto[]>();

    sortedRoots.forEach((root) => {
      const letter = getRootLetter(root.name);
      const existingGroup = grouped.get(letter);
      if (existingGroup) {
        existingGroup.push(root);
      } else {
        grouped.set(letter, [root]);
      }
    });

    return grouped;
  }, [sortedRoots]);
  const rootLetters = useMemo(() => {
    const letters = [...groupedRootsByLetter.keys()].filter((letter) => letter !== '#').sort();
    if (groupedRootsByLetter.has('#')) {
      letters.push('#');
    }

    return letters;
  }, [groupedRootsByLetter]);
  const rootLetterAnchors = useMemo(() => {
    const anchors = new Map<string, string>();

    rootLetters.forEach((letter) => {
      anchors.set(letter, `ruler-section-${letter}`);
    });

    return anchors;
  }, [rootLetters]);
  const hasFilter = normalizedQuery.length > 0;

  return (
    <div className="ruler-catalog-panel">
      <div className="filter-toolbar ruler-toolbar">
        <div className="filter-toolbar-row">
          <div className="filter-toolbar-left">
            <div className="filter-field">
              <label htmlFor="ruler-search" className="form-label">Filter:</label>
              <input
                id="ruler-search"
                type="text"
                className="form-control filter-control filter-control--primary filter-input"
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                placeholder="Issuer, ruler, period, title..."
              />
            </div>
            {searchText ? (
              <button type="button" className="btn btn--brand btn--compact" onClick={() => setSearchText('')}>
                Clear
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {loading ? <div className="loading-state">Loading ruler catalog...</div> : null}
      {error ? <div className="empty-state">{error}</div> : null}

      {!loading && !error && filteredRoots.length === 0 ? (
        <div className="empty-state">No rulers found for this filter.</div>
      ) : null}

      {!loading && !error && sortedRoots.length > 0 && rootLetters.length > 0 ? (
        <div className="letter-selector fade-in ruler-letter-selector">
          {rootLetters.map((letter, index) => (
            <span key={letter} className="letter-link">
              {index > 0 ? <span className="letter-separator">&middot;</span> : null}
              <a
                href={`#${rootLetterAnchors.get(letter)}`}
                onClick={(event) => {
                  event.preventDefault();
                  const targetId = rootLetterAnchors.get(letter);
                  if (!targetId) {
                    return;
                  }

                  const element = document.getElementById(targetId);
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
      ) : null}

      {!loading && !error && sortedRoots.length > 0 ? (
        <div className="ruler-tree">
          {rootLetters.map((letter) => (
            <div
              key={`ruler-section-${letter}`}
              id={rootLetterAnchors.get(letter)}
              className="issuer-section ruler-root-anchor"
            >
              <h3 className="issuer-section-header">{letter}</h3>
              <div className="ruler-letter-group">
                {(groupedRootsByLetter.get(letter) ?? []).map((root, index) => (
                  <RulerTreeNode
                    key={`${root.id ?? root.urlSlug ?? root.name ?? 'root'}-${index}`}
                    node={root}
                    level={0}
                    forceExpanded={hasFilter}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
