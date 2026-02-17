import { useMemo } from 'react';
import type { IssuerTreeViewNode } from './issuerTreeView.types';

/**
 * Hook to flatten and group the issuer tree by first letter.
 */
export function useAlphabeticalGrouping(
    filteredRoots: IssuerTreeViewNode[],
    isEnabled: boolean
) {
    return useMemo(() => {
        if (!isEnabled) return null;

        const grouped: Map<string, IssuerTreeViewNode[]> = new Map();

        const flattenTree = (
            nodes: IssuerTreeViewNode[],
            isTopLevel: boolean,
            rootName: string | null = null
        ): IssuerTreeViewNode[] => {
            let flat: IssuerTreeViewNode[] = [];

            for (const node of nodes) {
                const currentRootName = isTopLevel ? node.name : rootName;

                if (node.children.length > 0) {
                    flat = flat.concat(flattenTree(node.children, false, currentRootName));
                }

                if (node.children.length === 0) {
                    const { children, ...rest } = node;

                    let nodeName = node.name || '';
                    if (node.isHistoricalPeriod) {
                        nodeName = nodeName.replace(/\s*\(.*\)$/, '');
                    }

                    const isNameMatch = !!currentRootName && nodeName === currentRootName && !node.territoryType;
                    const effectivelyTopLevel = isTopLevel || isNameMatch;

                    const flatNode: IssuerTreeViewNode = {
                        ...rest,
                        children: [],
                        isTopLevelLeaf: effectivelyTopLevel,
                    };

                    flat.push(flatNode);
                }
            }

            return flat;
        };

        const flatNodes = flattenTree(filteredRoots, true);
        flatNodes.sort((a, b) => (a.name || '').localeCompare(b.name || ''));

        for (const node of flatNodes) {
            let name = node.name || '';

            // Remove leading punctuation/symbols but keep letters/numbers from all alphabets.
            name = name.replace(/^[^\p{L}\p{N}]+/u, '').trim();

            // Characters not fully normalized by NFD.
            name = name.replace(/\u0110/g, 'D').replace(/\u0111/g, 'd');

            const normalizedName = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
            const firstChar = normalizedName.trim().charAt(0).toUpperCase();
            const key = /[A-Z]/.test(firstChar) ? firstChar : '#';

            if (!grouped.has(key)) {
                grouped.set(key, []);
            }

            grouped.get(key)?.push(node);
        }

        const sortedKeys = Array.from(grouped.keys()).sort((a, b) => {
            if (a === '#') return -1;
            if (b === '#') return 1;
            return a.localeCompare(b);
        });

        return { grouped, sortedKeys };
    }, [filteredRoots, isEnabled]);
}
