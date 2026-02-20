import { OpenAPI } from '../api/core/OpenAPI';
import { request as __request } from '../api/core/request';
import type { CancelablePromise } from '../api/core/CancelablePromise';
import type { CatalogIssuerRulerNodeDto } from '../models/CatalogIssuerRulerNodeDto';

export class CatalogBrowseService {
    /**
     * @returns CatalogIssuerRulerNodeDto OK
     * @throws ApiError
     */
    public static getRulerBrowser(): CancelablePromise<Array<CatalogIssuerRulerNodeDto>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/catalog/ruler-browser',
        });
    }
}
