import { useState, memo } from 'react';
import type { IssuerTreeDto } from '../../models/IssuerTreeDto';
import './IssuerNode.css';

interface IssuerNodeProps {
    node: IssuerTreeDto;
    onSelect: (node: IssuerTreeDto) => void;
    level?: number;
    forceExpanded?: boolean;
    showFlag?: boolean;
    disableIndent?: boolean;
}

export const IssuerNode = memo(function IssuerNode({ node, onSelect, level = 0, forceExpanded = false, showFlag = true, disableIndent = false }: IssuerNodeProps) {
    // Condition:
    // 1. Roots (ParentId == null, TopParentId == null) -> Expanded (Shows Level 1)
    // 2. Level 1 (ParentId == TopParentId) -> Expanded (Shows Level 2)
    // 3. Level 2+ (ParentId != TopParentId) -> Collapsed (Hides deeper levels)
    // We use loose equality (==) to handle null/undefined matches.
    const isAlwaysExpanded = node.parentId == node.topParentId;

    const [isExpandedState, setIsExpandedState] = useState(false);

    // Effective expanded state
    const isExpanded = isAlwaysExpanded || isExpandedState || forceExpanded;
    const hasChildren = node.children && node.children.length > 0;
    const isLeaf = !node.isSection;

    const handleToggle = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (hasChildren && !isAlwaysExpanded) {
            setIsExpandedState(!isExpandedState);
        }
    };

    const handleSelect = (e: React.MouseEvent) => {
        e.stopPropagation();
        onSelect(node);
    };

    const indentation = disableIndent ? 0 : (level === 0 ? 0 : 20);

    return (
        <div className="issuer-node" style={{ paddingLeft: `${indentation}px` }}> {/* Simple indent for now, CSS can handle it too */}
            <div
                className={`issuer-row ${isLeaf ? 'is-leaf' : 'is-section'} ${isAlwaysExpanded ? 'always-expanded' : ''} ${level === 0 ? 'is-root' : ''} ${node.isHistoricalPeriod ? 'is-historical' : ''}`}
            >

                {/* Expand/Collapse Icon */}
                <span
                    className={`toggle-icon ${isExpanded ? 'expanded' : ''}`}
                    onClick={handleToggle}
                >
                    {hasChildren && !isAlwaysExpanded ? '▶' : <span className="spacer"></span>}
                </span>

                {/* Flag */}
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
                            forceExpanded={!!(child as any).forceExpanded}
                        />
                    ))}
                </div>
            )}
        </div>
    );
});
