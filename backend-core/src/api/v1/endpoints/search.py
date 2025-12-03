import logging
import base64
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
# [추가] 유효성 검사 에러 처리를 위한 임포트
from pydantic import ValidationError 

from src.api import deps
from src.crud.crud_product import crud_product
from src.schemas.product import ProductResponse
from src.models.product import Product
from src.config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ai-search", response_model=Dict[str, Any])
async def ai_search(
    query: str = Form(..., description="사용자 검색 쿼리"),
    image_file: Optional[UploadFile] = File(None),
    limit: int = Form(10),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    통합 AI 기반 상품 검색
    """
    logger.info(f"Received search query: '{query}' with image: {image_file is not None}")

    # 1. 이미지 처리 (Base64 변환)
    image_b64: Optional[str] = None
    if image_file:
        try:
            content = await image_file.read()
            image_b64 = base64.b64encode(content).decode("utf-8")
        except Exception as e:
            logger.error(f"Image file read error: {e}")
            raise HTTPException(status_code=400, detail="이미지 파일을 읽을 수 없습니다.")

    # 2. AI Service 호출
    AI_SERVICE_API_URL = settings.AI_SERVICE_API_URL
    search_path = 'INTERNAL'
    reason = "AI 검색 결과입니다."
    vector: List[float] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        # A. 경로 결정 (Orchestrator)
        try:
            path_response = await client.post(
                f"{AI_SERVICE_API_URL}/determine-path", 
                json={"query": query}
            )
            if path_response.status_code == 200:
                search_path = path_response.json().get("path", 'INTERNAL')
        except Exception:
            pass # 실패 시 기본값 INTERNAL 유지

        # B. AI 처리 및 벡터 생성
        ai_endpoint = "/process-external" if search_path == 'EXTERNAL' else "/process-internal"
        
        try:
            ai_payload = {"query": query, "image_b64": image_b64}
            
            ai_data_response = await client.post(
                f"{AI_SERVICE_API_URL}{ai_endpoint}", 
                json=ai_payload
            )
            
            if ai_data_response.status_code != 200:
                logger.error(f"AI Service Error: {ai_data_response.text}")
                # AI 실패 시에도 502 대신 빈 리스트 처리하거나 에러 상세화
                raise HTTPException(status_code=502, detail="AI 분석 서비스 오류")

            ai_data = ai_data_response.json()
            vector = ai_data.get("vector", [])
            reason = ai_data.get("reason", reason)
            
        except httpx.RequestError as e:
            logger.error(f"AI Connection critical error: {e}")
            raise HTTPException(status_code=503, detail="AI 서비스 연결 실패")

    # 3. 벡터 유효성 검사
    if not vector:
        raise HTTPException(status_code=500, detail="AI 벡터 생성 실패 (Empty Vector)")

    # 4. DB 검색 (Threshold 적용)
    try:
        results: List[Product] = await crud_product.search_by_vector(
            db, 
            query_vector=vector, 
            limit=limit,
            threshold=1.2
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스 벡터 검색 오류")

    # 5. 결과 반환 (🛡️ 방어적 코딩 적용됨)
    # 기존 코드: product_responses = [ProductResponse.model_validate(p) for p in results]
    # 수정된 코드: 불량 데이터(이름 없음)가 있어도 죽지 않도록 필터링
    product_responses = []
    
    for p in results:
        # 1. 데이터 클렌징 (이름이 없거나 너무 짧으면 임시 이름 부여)
        clean_name = p.name
        if not clean_name or len(str(clean_name).strip()) < 2:
            clean_name = "이름 미정 상품"
        
        try:
            # 2. 안전하게 변환 (Pydantic 검증 시도)
            # ORM 객체를 직접 수정하지 않고 딕셔너리로 변환하여 검증
            p_dict = {
                "id": p.id,
                "name": clean_name, # 정제된 이름 사용
                "description": p.description or "",
                "price": p.price or 0,
                "stock_quantity": p.stock_quantity or 0,
                "category": p.category or "Etc",
                "image_url": p.image_url,
                "embedding": p.embedding,
                "is_active": p.is_active,
                "created_at": p.created_at,
                "updated_at": p.updated_at
            }
            product_responses.append(ProductResponse.model_validate(p_dict))
            
        except ValidationError as e:
            # 정말 복구 불가능한 데이터는 로그만 남기고 스킵 (500 에러 방지)
            logger.warning(f"⚠️ Skipping invalid product ID {p.id}: {e}")
            continue
    
    return {
        "status": "SUCCESS",
        "answer": reason,
        "products": product_responses,
        "search_path": search_path
    }

# 기타 Placeholder (구현 예정 기능들)
@router.get("/related-price/{product_id}")
async def get_related_by_price(product_id: int, db: AsyncSession = Depends(deps.get_db)):
    return {"message": "Pending implementation"}

@router.get("/ai-coordination/{product_id}")
async def get_ai_coordination(product_id: int, db: AsyncSession = Depends(deps.get_db)):
    return {"message": "Pending implementation"}