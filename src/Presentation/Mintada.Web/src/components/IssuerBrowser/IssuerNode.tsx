import { memo, useState, type MouseEvent } from 'react';
import type { IssuerTreeViewNode } from './issuerTreeView.types';
import './IssuerNode.css';

interface IssuerNodeProps {
    node: IssuerTreeViewNode;
    onSelect: (node: IssuerTreeViewNode) => void;
    level?: number;
    forceExpanded?: boolean;
    showFlag?: boolean;
    disableIndent?: boolean;
}

export const IssuerNode = memo(function IssuerNode({
    node,
    onSelect,
    level = 0,
    forceExpanded = false,
    showFlag = true,
    disableIndent = false,
}: IssuerNodeProps) {
    // Keep only root nodes expanded by default.
    // All deeper levels start collapsed unless expanded by filter/manual toggle.
    const isAlwaysExpanded = level === 0;

    const [isExpandedState, setIsExpandedState] = useState(level === 0);

    const isExpanded = isAlwaysExpanded || isExpandedState || forceExpanded;
    const hasChildren = node.children.length > 0;
    const isLeaf = !node.isSection;

    const handleToggle = (e: MouseEvent) => {
        e.stopPropagation();
        if (hasChildren && !isAlwaysExpanded) {
            setIsExpandedState(!isExpandedState);
        }
    };

    const handleSelect = (e: MouseEvent) => {
        e.stopPropagation();
        onSelect(node);
    };

    const indentation = disableIndent ? 0 : (level === 0 ? 0 : 20);

    return (
        <div className="issuer-node" style={{ paddingLeft: `${indentation}px` }}>
            <div
                className={`issuer-row catalog-tree-row catalog-tree-row--interactive ${level === 0 ? 'catalog-tree-row--root' : 'catalog-tree-row--item'} ${isLeaf ? 'is-leaf' : 'is-section'} ${isAlwaysExpanded ? 'always-expanded' : ''} ${level === 0 ? 'is-root' : ''} ${node.isHistoricalPeriod ? 'is-historical' : ''}`}
            >
                <span
                    className={`toggle-icon catalog-tree-toggle ${level === 0 ? 'catalog-tree-toggle--root' : ''} ${isExpanded ? 'expanded' : ''}`}
                    onClick={handleToggle}
                >
                    {hasChildren && !isAlwaysExpanded ? '\u25B6' : <span className={`spacer catalog-tree-toggle-spacer ${level === 0 ? 'catalog-tree-toggle-spacer--root' : ''}`}></span>}
                </span>

                {showFlag && (level === 0 || !node.parentId) && node.urlSlug && (
                    <span
                        className={`sprite s${node.urlSlug} issuer-flag`}
                        onClick={handleSelect}
                    ></span>
                )}

                <div className={`issuer-label catalog-tree-label ${level === 0 ? 'catalog-tree-label--baseline' : ''}`} onClick={handleSelect}>
                    <span className={`name catalog-link catalog-tree-name ${level === 0 ? 'catalog-tree-name--root' : ''}`}>{node.name}</span>
                    {node.territoryType && <span className="type catalog-tree-meta"> ({node.territoryType})</span>}
                </div>
            </div>

            {hasChildren && isExpanded && (
                <div className="issuer-children">
                    {node.children.map(child => (
                        <IssuerNode
                            key={child.id}
                            node={child}
                            onSelect={onSelect}
                            level={level + 1}
                            forceExpanded={!!child.forceExpanded}
                        />
                    ))}
                </div>
            )}
        </div>
    );
});
