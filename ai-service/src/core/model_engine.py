import os
import logging
import json
import random
from typing import List, Optional, Any

# LangChain 라이브러리
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ibm import ChatWatsonx
from langchain_core.messages import HumanMessage

# 로깅 설정
logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# Vision 지원 모델
VISION_MODEL_ID = "meta-llama/llama-3-2-11b-vision-instruct" 

class ModelEngine:
    _instance: Optional['ModelEngine'] = None
    
    def __init__(self):
        self.vision_model: Optional[ChatWatsonx] = None
        self.text_model: Optional[ChatWatsonx] = None
        self.embedding_model: Optional[HuggingFaceEmbeddings] = None
        self.project_id = os.getenv("WATSONX_PROJECT_ID")
        self.is_initialized = False

    def initialize(self):
        """모델 엔진 초기화"""
        logger.info(f"🚀 Initializing Model Engine (Multilingual)...")
        
        try:
            api_key = os.getenv("WATSONX_API_KEY")
            url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
            
            if api_key and self.project_id:
                # 1. Vision/Chat 모델 초기화
                self.vision_model = ChatWatsonx(
                    model_id=VISION_MODEL_ID,
                    url=url,
                    apikey=api_key,
                    project_id=self.project_id,
                    params={
                        "decoding_method": "greedy",
                        "max_new_tokens": 900,
                        "min_new_tokens": 1,
                        "temperature": 0.1
                    }
                )
                self.text_model = self.vision_model
                logger.info(f"✅ Watsonx Vision Model Loaded: {VISION_MODEL_ID}")
            else:
                logger.warning("⚠️ Watsonx credentials missing. AI features disabled.")

        except Exception as e:
            logger.error(f"❌ Watsonx Init Failed: {e}")

        # 2. 임베딩 모델 초기화
        try:
            logger.info(f"📥 Loading Embedding Model: {EMBEDDING_MODEL_NAME}...")
            self.embedding_model = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_NAME,
                model_kwargs={'device': os.getenv("EMBEDDING_DEVICE", "cpu")},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("✅ Embedding Model Loaded (Korean Supported).")
            self.is_initialized = True
        except Exception as e:
            logger.error(f"❌ Embedding Model Failed: {e}")

    def generate_embedding(self, text: str) -> List[float]:
        """텍스트 -> 벡터 변환"""
        if not self.embedding_model:
            self.initialize()
        if self.embedding_model:
            return self.embedding_model.embed_query(text)
        return [0.0] * 768

    def generate_text(self, prompt: str) -> str:
        """일반 텍스트 생성"""
        if not self.text_model:
            self.initialize()
        
        if self.text_model:
            try:
                response = self.text_model.invoke(prompt)
                return response.content
            except Exception as e:
                logger.error(f"Text Gen Error: {e}")
        return "AI Service Unavailable"

    def generate_with_image(self, text_prompt: str, image_b64: str) -> str:
        """
        [Vision] 이미지와 텍스트를 함께 처리
        """
        if not self.vision_model:
            self.initialize()
            
        if not self.vision_model:
            raise RuntimeError("AI Model not initialized")

        try:
            message = HumanMessage(
                content=[
                    {"type": "text", "text": text_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ]
            )
            response = self.vision_model.invoke([message])
            return response.content
            
        except Exception as e:
            logger.error(f"👁️ Vision Analysis Error: {e}")
            raise e

# 싱글톤 인스턴스
model_engine = ModelEngine()