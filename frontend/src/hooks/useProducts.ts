import { useQuery } from '@tanstack/react-query';
import client from '@/api/client';
import { ProductResponse } from '@/types/index';

/**
 * 상품 목록 조회
 */
export const useProductList = (skip: number = 0, limit: number = 20) => {
  return useQuery<ProductResponse[]>({
    queryKey: ['products', skip, limit],
    queryFn: async () => {
      // [FIX] '/v1' 제거 (client baseURL에 이미 포함됨)
      // 최종 요청: http://localhost:8000/api/v1/products/
      const { data } = await client.get(`/products/`, {
        params: { skip, limit }
      });
      return data;
    },
    staleTime: 60 * 1000,
  });
};

/**
 * 상품 상세 조회
 */
export const useProductDetail = (productId: number | string | undefined) => {
  return useQuery<ProductResponse>({
    queryKey: ['product', productId],
    queryFn: async () => {
      if (!productId) throw new Error("Product ID is undefined.");
      // [FIX] '/v1' 제거
      // 최종 요청: http://localhost:8000/api/v1/products/{id}
      const { data } = await client.get(`/products/${productId}`);
      return data;
    },
    enabled: !!productId && productId !== 'undefined', 
  });
};