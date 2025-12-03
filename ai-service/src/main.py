import logging
import json
import re
import base64
from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

from src.core.model_engine import model_engine
from src.core.prompts import VISION_ANALYSIS_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Service Starting...")
    try:
        model_engine.initialize()
    except Exception as e:
        logger.error(f"⚠️ Model init warning: {e}")
    yield
    logger.info("💤 AI Service Shutting down...")

app = FastAPI(title="Modify AI Service", version="1.0.0", lifespan=lifespan)
api_router = APIRouter(prefix="/api/v1")

# --- DTO ---
class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    vector: List[float]

class ImageAnalysisResponse(BaseModel):
    name: str
    category: str
    description: str
    price: int
    vector: List[float]

class PathRequest(BaseModel):
    query: str

class InternalSearchRequest(BaseModel):
    query: str
    image_b64: Optional[str] = None

class SearchProcessResponse(BaseModel):
    vector: List[float]
    reason: str

# --- Endpoints ---

@api_router.post("/embed-text", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    try:
        vector = model_engine.generate_embedding(request.text)
        return {"vector": vector}
    except:
        return {"vector": [0.0] * 768} 

@api_router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    filename = file.filename
    try:
        contents = await file.read()
        image_b64 = base64.b64encode(contents).decode("utf-8")
        
        prompt = VISION_ANALYSIS_PROMPT
        
        logger.info(f"👁️ Analyzing image: {filename}...")
        generated_text = model_engine.generate_with_image(prompt, image_b64)
        logger.info(f"🤖 Raw AI Response: {generated_text}")

        # [Safety Check]
        if "cannot assist" in generated_text or "I cannot" in generated_text:
            raise ValueError("AI Safety Filter Triggered")

        # [Parsing] JSON 추출
        product_data = {}
        try:
            # 1. 가장 먼저 발견되는 { ... } 블록 추출
            json_match = re.search(r"\{[\s\S]*\}", generated_text)
            if json_match:
                clean_json = json_match.group()
                # 마크다운 제거
                clean_json = re.sub(r"```json|```", "", clean_json)
                product_data = json.loads(clean_json)
            else:
                # 전체가 JSON일 경우
                product_data = json.loads(generated_text)
        except Exception as e:
            logger.warning(f"JSON Parsing failed: {e}. Raw: {generated_text[:50]}...")

        # [Data Validation & Fallback]
        final_name = product_data.get("name")
        # 이름이 비었거나 프롬프트 내용을 앵무새처럼 따라한 경우 체크
        if not final_name or "상품명" in final_name or "JSON" in final_name:
             final_name = f"AI 추천 상품 ({filename.split('.')[0]})"
        
        final_desc = product_data.get("description")
        if not final_desc or len(final_desc) < 10:
            final_desc = "AI가 이미지를 분석하여 추천하는 상품입니다. 매력적인 스타일과 뛰어난 품질을 자랑합니다."
            
        final_cat = product_data.get("category", "Uncategorized")
        
        # 가격 처리
        try:
            raw_price = str(product_data.get("price", 0))
            price = int(re.sub(r"[^0-9]", "", raw_price))
        except:
            price = 0

        # 벡터 생성 (검색용)
        meta_text = f"{final_name} {final_cat} {final_desc}"
        vector = model_engine.generate_embedding(meta_text)

        return {
            "name": final_name,
            "category": final_cat,
            "description": final_desc,
            "price": price,
            "vector": vector
        }

    except Exception as e:
        logger.error(f"❌ Analysis Error: {e}")
        return {
            "name": f"등록된 상품 ({filename})",
            "category": "Etc",
            "description": "이미지 분석에 실패했습니다. 관리자 모드에서 정보를 수정해주세요.",
            "price": 0,
            "vector": [0.0] * 768
        }

@api_router.post("/llm-generate-response")
async def llm_generate(body: Dict[str, str]):
    prompt = body.get("prompt", "")
    try:
        korean_prompt = f"질문: {prompt}\n답변 (한국어):"
        answer = model_engine.generate_text(korean_prompt)
        return {"answer": answer}
    except:
        return {"answer": "죄송합니다. AI 응답을 생성할 수 없습니다."}

@api_router.post("/determine-path")
async def determine_path(request: PathRequest):
    return {"path": "INTERNAL"}

@api_router.post("/process-internal", response_model=SearchProcessResponse)
async def process_internal(request: InternalSearchRequest):
    query = request.query
    vector = model_engine.generate_embedding(query)
    return {"vector": vector, "reason": f"'{query}' 검색 결과입니다."}

@api_router.post("/process-external", response_model=SearchProcessResponse)
async def process_external(request: InternalSearchRequest):
    return await process_internal(request)

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Modify AI Service is Running"}