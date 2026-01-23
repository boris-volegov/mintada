/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CoinTypeDto } from '../models/CoinTypeDto';
import type { IssuerDto } from '../models/IssuerDto';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class IssuersService {
    /**
     * @returns IssuerDto OK
     * @throws ApiError
     */
    public static getApiIssuers(): CancelablePromise<Array<IssuerDto>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/Issuers',
        });
    }
    /**
     * @param id
     * @returns CoinTypeDto OK
     * @throws ApiError
     */
    public static getApiIssuersCoinTypes(
        id: number,
    ): CancelablePromise<Array<CoinTypeDto>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/Issuers/{id}/coin-types',
            path: {
                'id': id,
            },
        });
    }
    /**
     * @param slug
     * @returns CoinTypeDto OK
     * @throws ApiError
     */
    public static getApiIssuersCoinTypes1(
        slug: string,
    ): CancelablePromise<Array<CoinTypeDto>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/Issuers/{slug}/coin-types',
            path: {
                'slug': slug,
            },
        });
    }
}
