from typing import List, Optional, Any, Union, Dict
from datetime import datetime
from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product import Product
from src.schemas.product import ProductCreate, ProductUpdate 

class CRUDProduct:
    """상품 모델에 대한 비동기 CRUD 및 벡터 검색 연산을 담당하는 클래스"""

    # --- [기존 CRUD 함수들 유지] ---
    async def get(self, db: AsyncSession, product_id: int) -> Optional[Product]:
        stmt = select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_multi(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[Product]:
        stmt = select(Product).where(Product.deleted_at.is_(None)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: Union[ProductCreate, Dict[str, Any]]) -> Product:
        if isinstance(obj_in, dict): create_data = obj_in
        else: create_data = obj_in.model_dump(exclude_unset=True)
        db_obj = Product(**create_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(self, db: AsyncSession, *, db_obj: Product, obj_in: Union[ProductUpdate, Dict[str, Any]]) -> Product:
        if isinstance(obj_in, dict): update_data = obj_in
        else: update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items(): setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def soft_delete(self, db: AsyncSession, *, product_id: int) -> Product:
        now = datetime.now()
        stmt = update(Product).where(Product.id == product_id).values(deleted_at=now)
        await db.execute(stmt)
        await db.commit()
        return await self.get(db, product_id)

    # -------------------------------------------------------
    # 🚨 [FIX] 벡터 검색: Threshold(유사도 커트라인) 복구
    # -------------------------------------------------------
    async def search_by_vector(
        self, 
        db: AsyncSession, 
        query_vector: List[float], 
        limit: int = 10,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        exclude_id: Optional[List[int]] = None,
        exclude_category: Optional[List[str]] = None,
        threshold: float = 1.2 
    ) -> List[Product]:
        """
        벡터 유사도 기반 상품 검색 (관련 없는 상품 필터링)
        """
        # 1. 거리 계산식 (L2 Distance)
        distance_col = Product.embedding.l2_distance(query_vector)
        
        # 2. 쿼리 구성 (거리순 정렬)
        stmt = select(Product).order_by(distance_col)
        
        # 3. 기본 필터
        stmt = stmt.filter(Product.is_active == True)
        stmt = stmt.filter(Product.deleted_at.is_(None))
        stmt = stmt.filter(Product.embedding.is_not(None))
        
        # 4. [핵심] 차단막 적용! (거리가 threshold보다 작아야 함)
        stmt = stmt.filter(distance_col < threshold)

        # 5. 추가 필터링
        if min_price is not None: stmt = stmt.filter(Product.price >= min_price)
        if max_price is not None: stmt = stmt.filter(Product.price <= max_price)
        if exclude_id: stmt = stmt.filter(Product.id.notin_(exclude_id))
        if exclude_category: stmt = stmt.filter(Product.category.notin_(exclude_category))

        # 6. 개수 제한
        stmt = stmt.limit(limit)
        
        result = await db.execute(stmt)
        return result.scalars().all()

# 싱글톤 객체 생성
crud_product = CRUDProduct()