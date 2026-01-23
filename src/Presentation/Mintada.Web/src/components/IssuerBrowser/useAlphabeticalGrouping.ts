import { useMemo } from 'react';
import type { IssuerTreeDto } from '../../models/IssuerTreeDto';

/**
 * Hook to handle flattening and grouping the issuer tree by first letter.
 */
export function useAlphabeticalGrouping(
    filteredRoots: IssuerTreeDto[],
    isEnabled: boolean
) {
    return useMemo(() => {
        if (!isEnabled) return null;

        // --- ALPHABETICAL GROUPING MODE ---

        // Group roots by first letter
        const grouped: Map<string, IssuerTreeDto[]> = new Map();

        // Helper to flatten the tree AND only keep leaf nodes (no children)
        // Recursion finds deep leaves.
        const flattenTree = (nodes: IssuerTreeDto[], isTopLevel: boolean, rootName: string | null = null): IssuerTreeDto[] => {
            let flat: IssuerTreeDto[] = [];
            nodes.forEach(node => {
                const currentRootName = isTopLevel ? node.name : rootName;

                // 1. Recurse first to find children (if any)
                if (node.children && node.children.length > 0) {
                    // Pass false for isTopLevel as we dive deeper
                    flat = flat.concat(flattenTree(node.children, false, currentRootName));
                }

                // 2. Add THIS node only if it is a leaf (no children)
                if (!node.children || node.children.length === 0) {
                    const { children, ...rest } = node;

                    // Determine if this leaf should be treated as top-level:
                    // 1. It IS a top-level node (no parents in this context)
                    // 2. It matches the root parent's name (e.g. "Switzerland" -> "Switzerland")
                    //    AND it does NOT have a territoryType (e.g. "Municipality", "City")
                    //    Exception: If Historical Period, ignore any suffix in parentheses (e.g. dates, other info).
                    let nodeName = node.name || '';
                    if (node.isHistoricalPeriod) {
                        nodeName = nodeName.replace(/\s*\(.*\)$/, '');
                    }

                    const isNameMatch = currentRootName && nodeName === currentRootName && !node.territoryType;
                    const effectivelyTopLevel = isTopLevel || isNameMatch;

                    const flatNode = { ...rest, _isTopLevel: effectivelyTopLevel } as unknown as IssuerTreeDto;
                    flat.push(flatNode);
                }
            });
            return flat;
        };

        // Start flattening with isTopLevel = true for the roots
        const flatNodes = flattenTree(filteredRoots, true);

        // Sort all flat nodes alphabetically first (to ensure order within groups)
        flatNodes.sort((a, b) => (a.name || "").localeCompare(b.name || ""));

        flatNodes.forEach(node => {
            let name = node.name || "";
            const originalName = name; // Debugging

            // 1. Remove leading punctuation/symbols (anything that is NOT a Letter or Number)
            // We use Unicode property escapes (\p{L} for Letter, \p{N} for Number) to preserve diacritics like 'É'.
            // The 'u' flag is essential.
            name = name.replace(/^[^\p{L}\p{N}]+/u, "").trim();

            // 2. Manual replacements for chars resistant to NFD (like Đ/đ -> D/d)
            name = name.replace(/Đ/g, "D").replace(/đ/g, "d");

            // 3. Standard Normalization
            const normalizedName = name.normalize("NFD").replace(/[\u0300-\u036f]/g, "");

            const firstChar = normalizedName.trim().charAt(0).toUpperCase();
            // Handle non-letters (put in '#')
            const key = /[A-Z]/.test(firstChar) ? firstChar : '#';

            // DEBUGGING: Log why item went to #
            if (key === '#') {
                const charCodes = originalName.split('').map(c => c.charCodeAt(0)).join(', ');
                console.warn(`[IssuerSorting] Item grouped into '#':\nOriginal="${originalName}"\nCleaned="${name}"\nFirstChar="${firstChar}"\nCharCodes=[${charCodes}]`);
            }

            if (!grouped.has(key)) grouped.set(key, []);
            grouped.get(key)?.push(node);
        });

        // Sort keys (numbers/# first, then A-Z)
        const sortedKeys = Array.from(grouped.keys()).sort((a, b) => {
            if (a === '#') return -1;
            if (b === '#') return 1;
            return a.localeCompare(b);
        });

        return { grouped, sortedKeys };
    }, [filteredRoots, isEnabled]);
}
