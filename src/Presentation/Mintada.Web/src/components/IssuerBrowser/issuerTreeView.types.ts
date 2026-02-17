import type { IssuerTreeDto } from '../../models/IssuerTreeDto';

export type IssuerTreeViewNode = Omit<IssuerTreeDto, 'children'> & {
  children: IssuerTreeViewNode[];
  forceExpanded?: boolean;
  containsStrictMatch?: boolean;
  isTopLevelLeaf?: boolean;
};

