import type { IssuerDto } from '../api/models/IssuerDto';
import type { CatalogRulerDto } from './CatalogRulerDto';

export type CatalogIssuerRulerNodeDto = IssuerDto & {
    children: CatalogIssuerRulerNodeDto[];
    rulers: CatalogRulerDto[];
    leafIssuerCountWithRulers: number;
    rulerCountInSubtree: number;
};
