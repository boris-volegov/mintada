import { OpenAPI } from '../api/core/OpenAPI';
import { request as __request } from '../api/core/request';
import type { CancelablePromise } from '../api/core/CancelablePromise';
import type { IssuerTreeDto } from '../models/IssuerTreeDto';

export class IssuerTreeService {
    /**
     * @returns IssuerTreeDto OK
     * @throws ApiError
     */
    public static getIssuerHierarchy(): CancelablePromise<Array<IssuerTreeDto>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/issuers/hierarchy',
        });
    }
}
