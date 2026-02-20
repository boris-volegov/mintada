import { useEffect, useMemo, useState } from 'react';
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

interface RulerTreeNodeProps {
  node: CatalogIssuerRulerNodeDto;
  level: number;
  forceExpanded: boolean;
}

function RulerTreeNode({ node, level, forceExpanded }: RulerTreeNodeProps) {
  const hasChildren = node.children.length > 0;
  const hasRulers = node.rulers.length > 0;
  const canExpand = hasChildren || hasRulers;
  const [isExpanded, setIsExpanded] = useState(level <= 1);

  useEffect(() => {
    if (forceExpanded) {
      setIsExpanded(true);
    }
  }, [forceExpanded]);

  const expanded = forceExpanded || isExpanded;
  const rowIndent = Math.max(0, level - 1) * 18;
  const { ungrouped, groups } = useMemo(() => groupRulersForDisplay(node.rulers), [node.rulers]);

  return (
    <div className="ruler-node">
      <div className="ruler-node-row" style={{ paddingLeft: `${rowIndent}px` }}>
        <button
          type="button"
          className={`ruler-toggle ${expanded ? 'expanded' : ''}`}
          disabled={!canExpand}
          onClick={() => setIsExpanded((prev) => !prev)}
          aria-label={expanded ? 'Collapse node' : 'Expand node'}
        >
          {canExpand ? '\u25B6' : '\u00B7'}
        </button>

        <div className="ruler-node-title">
          <span className="ruler-node-name">{node.name ?? 'Unnamed issuer'}</span>
          {node.isHistoricalPeriod ? <span className="ruler-node-tag">Historical</span> : null}
        </div>
      </div>

      {expanded ? (
        <div className="ruler-node-details">
          {hasRulers ? (
            <div className="ruler-groups">
              {ungrouped.length > 0 ? (
                <ul className="ruler-list">
                  {ungrouped.map((ruler, index) => (
                    <li key={`ungrouped-${ruler.id}-${ruler.ruleType ?? ''}-${index}`} className="ruler-list-item">
                      <span className="ruler-name">{ruler.name}</span>
                      {ruler.ruleType ? <span className="ruler-meta">{ruler.ruleType}</span> : null}
                      {ruler.title ? <span className="ruler-meta">{ruler.title}</span> : null}
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
                        className="ruler-list-item"
                      >
                        <span className="ruler-name">{ruler.name}</span>
                        {ruler.ruleType ? <span className="ruler-meta">{ruler.ruleType}</span> : null}
                        {ruler.title ? <span className="ruler-meta">{ruler.title}</span> : null}
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
  const hasFilter = normalizedQuery.length > 0;

  return (
    <div className="ruler-catalog-panel">
      <div className="ruler-toolbar">
        <label htmlFor="ruler-search" className="form-label">Filter:</label>
        <input
          id="ruler-search"
          type="text"
          className="form-control filter-input"
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          placeholder="Issuer, ruler, period, title..."
        />
        {searchText ? (
          <button type="button" className="btn btn--brand btn--compact" onClick={() => setSearchText('')}>
            Clear
          </button>
        ) : null}
      </div>

      {loading ? <div className="loading-state">Loading ruler catalog...</div> : null}
      {error ? <div className="empty-state">{error}</div> : null}

      {!loading && !error && filteredRoots.length === 0 ? (
        <div className="empty-state">No rulers found for this filter.</div>
      ) : null}

      {!loading && !error && filteredRoots.length > 0 ? (
        <div className="ruler-tree">
          {filteredRoots.map((root, index) => (
            <RulerTreeNode
              key={`${root.id ?? root.urlSlug ?? root.name ?? 'root'}-${index}`}
              node={root}
              level={0}
              forceExpanded={hasFilter}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
