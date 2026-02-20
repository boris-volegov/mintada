import type { RulerIssuerCoinTypeGroupDto } from './RulerIssuerCoinTypeGroupDto';

export type RulerCoinTypesResponseDto = {
  rulerId: number;
  rulerName: string;
  portraitUrl?: string | null;
  infoHtml?: string | null;
  hasMultipleIssuers: boolean;
  issuerGroups: RulerIssuerCoinTypeGroupDto[];
};
