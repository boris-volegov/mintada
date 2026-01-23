import { useMemo } from 'react';
import type { IssuerTreeDto } from '../models/IssuerTreeDto';

export function useIssuerFilter(
    roots: IssuerTreeDto[],
    filterText: string,
    sortOption: string
) {
    return useMemo(() => {
        if (!filterText && sortOption === 'default') return roots;

        const normalizeText = (text: string) =>
            text.normalize("NFD")
                .toLowerCase()
                // Replace diacritics
                .replace(/[\u0300-\u036f]/g, "")
                // Replace any non-alphanumeric characters (like hyphens, brackets) with space
                .replace(/[^a-z0-9]/g, " ")
                // Collapse multiple spaces
                .replace(/\s+/g, " ")
                .trim();

        const normalizedFilter = normalizeText(filterText);

        const filterNode = (node: IssuerTreeDto, forceKeep: boolean = false): IssuerTreeDto | null => {
            // 1. Determine if this node matches strictly
            // Always calculate match for expansion purposes
            const normalizedName = normalizeText(node.name || "");

            // Direct "starts with" match (treating separators as spaces)
            const directMatch = normalizedName.startsWith(normalizedFilter);

            // Word-based match (any individual word starts with filter)
            const nameWords = normalizedName.split(" ");
            const wordMatch = nameWords.some(word => word.startsWith(normalizedFilter));

            const strictMatch = directMatch || wordMatch;

            // 2. Should we show this node and all its descendants?
            // Yes if we were forced by parent, or if we matched strictly ourselves.
            const shouldKeepAndForceChildren = forceKeep || strictMatch;

            // 3. Process children
            let filteredChildren: IssuerTreeDto[] = [];
            let hasStrictMatchingDescendant = false;

            if (node.children) {
                for (const child of node.children) {
                    // Pass 'shouldKeepAndForceChildren' down. If true, child will be forced to show.
                    const filteredChild = filterNode(child, shouldKeepAndForceChildren);
                    if (filteredChild) {
                        filteredChildren.push(filteredChild);
                        // Check if child strictly matched or has strict matching descendants
                        if ((filteredChild as any)._containsStrictMatch) {
                            hasStrictMatchingDescendant = true;
                        }
                    }
                }
            }

            // Sort children if needed
            if (sortOption === 'name_asc') {
                filteredChildren.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
            }

            // 4. Final Decision
            // We return the node if:
            // - We are forced/matched (shouldKeepAndForceChildren is true)
            // - OR We have children that matched (path to those children)
            const hasChildren = filteredChildren.length > 0;

            const containsStrictMatch = strictMatch || hasStrictMatchingDescendant;
            // Expand if we contain a strict match (ourselves or descendants)
            const shouldExpand = containsStrictMatch;

            if (shouldKeepAndForceChildren || hasChildren) {
                return {
                    ...node,
                    children: filteredChildren,
                    forceExpanded: shouldExpand,
                    _containsStrictMatch: containsStrictMatch
                } as any;
            }

            return null;
        };

        const results: IssuerTreeDto[] = [];
        for (const root of roots) {
            const filteredRoot = filterNode(root);
            if (filteredRoot) {
                results.push(filteredRoot);
            }
        }

        if (sortOption === 'name_asc') {
            results.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        }

        return results;
    }, [roots, filterText, sortOption]);
}
