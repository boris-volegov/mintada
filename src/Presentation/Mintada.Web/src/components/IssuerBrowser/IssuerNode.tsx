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
    // Keep root and first child level expanded to preserve the current UX.
    const isAlwaysExpanded = level <= 1;

    const [isExpandedState, setIsExpandedState] = useState(false);

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
                className={`issuer-row ${isLeaf ? 'is-leaf' : 'is-section'} ${isAlwaysExpanded ? 'always-expanded' : ''} ${level === 0 ? 'is-root' : ''} ${node.isHistoricalPeriod ? 'is-historical' : ''}`}
            >
                <span
                    className={`toggle-icon ${isExpanded ? 'expanded' : ''}`}
                    onClick={handleToggle}
                >
                    {hasChildren && !isAlwaysExpanded ? '\u25B6' : <span className="spacer"></span>}
                </span>

                {showFlag && (level === 0 || !node.parentId) && node.urlSlug && (
                    <span
                        className={`sprite s${node.urlSlug} issuer-flag`}
                        onClick={handleSelect}
                    ></span>
                )}

                <div className="issuer-label" onClick={handleSelect}>
                    <span className="name">{node.name}</span>
                    {node.territoryType && <span className="type"> ({node.territoryType})</span>}
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
