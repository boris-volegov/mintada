import type { RulerCoinTypeItemDto } from './RulerCoinTypeItemDto';

export type RulerIssuerCoinTypeGroupDto = {
  issuerId: number;
  issuerName?: string | null;
  issuerUrlSlug?: string | null;
  territoryType?: string | null;
  coinTypes: RulerCoinTypeItemDto[];
};
