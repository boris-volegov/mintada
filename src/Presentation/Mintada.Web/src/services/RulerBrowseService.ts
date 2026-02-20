import { OpenAPI } from '../api/core/OpenAPI';
import { request as __request } from '../api/core/request';
import type { CancelablePromise } from '../api/core/CancelablePromise';
import type { RulerCoinTypesResponseDto } from '../models/RulerCoinTypesResponseDto';

export class RulerBrowseService {
  public static getRulerCoinTypes(
    id: number | string,
  ): CancelablePromise<RulerCoinTypesResponseDto> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/rulers/{id}/coin-types',
      path: {
        id,
      },
    });
  }
}
