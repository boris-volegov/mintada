import type { IssuerTreeDto, IssuerDto } from '../../api';
import { IssuerNode } from './IssuerNode';

interface DefaultIssuerLayoutProps {
    filteredRoots: IssuerTreeDto[];
    onSelect: (issuer: IssuerDto) => void;
}

export function DefaultIssuerLayout({ filteredRoots, onSelect }: DefaultIssuerLayoutProps) {
    // --- DEFAULT LAYOUT (Original) ---
    // Heuristic: Calculate "weight" of each node (1 + children count) to better balance columns
    const getNodeWeight = (node: IssuerTreeDto): number => {
        let weight = 1; // Visual weight of the root (always visible)
        // Only count immediate children (Level 2).
        // Level 3 and below are collapsed by default per user feedback.
        if (node.children) {
            weight += node.children.length;
        }
        return weight;
    };

    const nodesWithWeights = filteredRoots.map(node => ({ node, weight: getNodeWeight(node) }));
    const totalWeight = nodesWithWeights.reduce((sum, item) => sum + item.weight, 0);
    const targetColWeight = totalWeight / 3;

    const columns: IssuerTreeDto[][] = [[], [], []];
    let currentCol = 0;
    let currentColWeight = 0;

    nodesWithWeights.forEach(({ node, weight }) => {
        // If adding this node pushes us way over target, and we aren't at the last column, switch
        // But we must at least put one item if column is empty
        if (currentCol < 2 && currentColWeight + weight / 2 > targetColWeight && columns[currentCol].length > 0) {
            currentCol++;
            currentColWeight = 0;
        }
        columns[currentCol].push(node);
        currentColWeight += weight;
    });

    return (
        <div className="issuer-columns-container">
            {columns.map((colItems, colIndex) => (
                <div key={colIndex} className="issuer-column">
                    {colItems.map(node => (
                        <IssuerNode
                            key={node.id}
                            node={node}
                            onSelect={onSelect}
                            forceExpanded={!!(node as any).forceExpanded}
                        />
                    ))}
                </div>
            ))}
        </div>
    );
}
