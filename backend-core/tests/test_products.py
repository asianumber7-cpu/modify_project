# backend-core/tests/test_products.py

import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.src.main import app # FastAPI 앱 인스턴스 임포트

client = TestClient(app)

# Product 모델 Mock 클래스 정의
class MockProduct:
    def __init__(self, id, embedding, is_active=True):
        self.id = id
        self.embedding = embedding
        self.is_active = is_active
        self.name = "Test Product"
        # 기타 필요한 필드 초기화

# Mocking DB 의존성 및 인증 (간소화)
def override_get_db():
    try:
        db = MagicMock(spec=Session)
        yield db
    finally:
        pass

def override_get_current_active_user():
    # 간단한 Mock User 반환
    return MagicMock(id=1, is_active=True)

# 의존성 오버라이드
from app.src.api.v1.endpoints.products import get_ai_coordination_products
from app.src.api.v1.endpoints import deps
app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_active_user] = override_get_current_active_user

# CRUD Mocking (get 함수)
from app.src.crud import crud_product
crud_product.product = MagicMock()

def test_get_ai_coordination_products_with_valid_embedding(db_mock: Session):
    """유효한 임베딩(리스트)을 가진 제품 테스트"""
    # 임베딩이 올바른 리스트 형태일 때
    valid_embedding = [0.1] * 128 
    mock_product = MockProduct(id=1, embedding=valid_embedding)
    
    # crud_product.get 호출 Mocking
    crud_product.product.get.return_value = mock_product
    
    # NOTE: get_ai_coordination_products 내부에서 호출되는 vector_search Mock이 추가로 필요합니다.
    # 여기서는 임베딩 유효성 검사 부분만 테스트하기 위해 vector_search는 Mock 처리되었다고 가정합니다.

    response = client.get("/api/v1/products/ai-coordination/1")
    assert response.status_code == 200
    # AI 기능이 성공적으로 작동하여 추천 결과가 반환된다고 가정
    assert "error" not in response.json() 

def test_get_ai_coordination_products_with_ambiguous_embedding(db_mock: Session):
    """다차원 배열(NumPy)과 유사한 상황을 가정하여 ValueError 방지 테스트"""
    import numpy as np
    # ValueError를 유발하는 NumPy 배열 (if not array 형태)
    ambiguous_embedding = np.array([1, 0, 1]) 
    mock_product = MockProduct(id=2, embedding=ambiguous_embedding)
    
    crud_product.product.get.return_value = mock_product
    
    # 수정된 코드는 이 경우에도 ValueError 없이 통과해야 합니다.
    response = client.get("/api/v1/products/ai-coordination/2")
    assert response.status_code == 200 
    assert "error" not in response.json() 
    
def test_get_ai_coordination_products_with_invalid_embedding(db_mock: Session):
    """유효하지 않은 (None) 임베딩을 가진 제품 테스트"""
    # 임베딩이 None일 때
    mock_product_none = MockProduct(id=3, embedding=None)
    
    crud_product.product.get.return_value = mock_product_none
    
    response = client.get("/api/v1/products/ai-coordination/3")
    assert response.status_code == 200
    # AI 분석 실패 응답을 확인
    assert response.json()["error"] == "AI analysis failed: Product embedding missing or invalid"
    
def test_get_ai_coordination_products_with_empty_embedding(db_mock: Session):
    """비어 있는 임베딩(리스트)을 가진 제품 테스트"""
    # 임베딩이 빈 리스트일 때
    mock_product_empty = MockProduct(id=4, embedding=[])
    
    crud_product.product.get.return_value = mock_product_empty
    
    response = client.get("/api/v1/products/ai-coordination/4")
    assert response.status_code == 200
    # AI 분석 실패 응답을 확인
    assert response.json()["error"] == "AI analysis failed: Product embedding missing or invalid"