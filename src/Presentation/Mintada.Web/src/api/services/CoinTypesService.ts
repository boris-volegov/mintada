/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CoinTypeDetailDto } from '../models/CoinTypeDetailDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CoinTypesService {
    /**
     * @param id
     * @returns CoinTypeDetailDto OK
     * @throws ApiError
     */
    public static getApiCoinTypes(
        id: number | string,
    ): CancelablePromise<CoinTypeDetailDto> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/coin-types/{id}',
            path: {
                'id': id,
            },
        });
    }
}
