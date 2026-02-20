export type RulerCoinTypeItemDto = {
  id: number;
  title: string;
  subtitle?: string | null;
  period?: string | null;
  rarityIndex?: number | null;
  coinTypeSlug: string;
  dateTimeInserted: string;
  issueTypeId: number;
  obverseImage?: string | null;
  reverseImage?: string | null;
};
