import type { IssuerDto } from '../api/models/IssuerDto';

export type IssuerTreeDto = IssuerDto & {
    children: IssuerTreeDto[];
};
