import os
import sys
from dotenv import load_dotenv

# .env.dev 파일 로드
load_dotenv(".env.dev")

try:
    from ibm_watsonx_ai import APIClient
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
except ImportError:
    print("❌ 'ibm-watsonx-ai' 패키지가 설치되지 않았습니다. pip install ibm-watsonx-ai 실행 필요.")
    sys.exit(1)

def check_connection():
    print("="*60)
    print("🕵️‍♂️ IBM Watsonx 연결 진단 도구 (Diagnostic Tool)")
    print("="*60)

    # 1. 환경변수 확인
    api_key = os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    print(f"📌 [설정 확인]")
    print(f"   - URL: {url}")
    print(f"   - Project ID: {project_id}")
    print(f"   - API Key: {'*' * 10}{api_key[-4:] if api_key else 'None'}")

    if not api_key or not project_id:
        print("\n❌ [오류] API Key 또는 Project ID가 .env 파일에 없습니다.")
        return

    # 2. 인증(Credentials) 테스트
    credentials = {
        "url": url,
        "apikey": api_key
    }
    
    print("\n🔄 [1단계] API Client 인증 시도 중...")
    try:
        client = APIClient(credentials)
        client.set.default_project(project_id)
        print("   ✅ API Client 객체 생성 성공")
    except Exception as e:
        print(f"   ❌ [인증 실패] API Key 또는 URL을 확인하세요.\n   에러: {e}")
        return

    # 3. 모델 리스트 조회 (권한 및 프로젝트 연결 확인)
    print("\n🔄 [2단계] 사용 가능한 파운데이션 모델 조회 시도 (권한 확인)...")
    try:
        models = client.foundation_models.get_model_specs()
        print(f"   ✅ 연결 성공! 조회된 모델 수: {len(models['resources'])}")
    except Exception as e:
        print(f"   ❌ [권한 실패] Project ID 연결 상태를 확인해야 합니다.")
        print(f"   에러 메시지: {e}")
        
        if "no_associated_service_instance_error" in str(e):
            print("\n   💡 [해결 방법]")
            print("   IBM Cloud 콘솔 -> Projects -> 해당 프로젝트 선택 -> 'Manage' 탭")
            print("   -> 'Services & Integrations' -> 'Associate Service'")
            print("   -> 'Watson Machine Learning' 서비스를 선택하여 연결해야 합니다!")
        return

    # 4. 실제 생성 테스트 (Inference)
    print("\n🔄 [3단계] 텍스트 생성 테스트 (LLM Inference)...")
    try:
        model_id = "ibm/granite-13b-chat-v2"
        params = {
            GenParams.DECODING_METHOD: "greedy",
            GenParams.MAX_NEW_TOKENS: 20
        }
        
        model = ModelInference(
            model_id=model_id,
            params=params,
            credentials=credentials,
            project_id=project_id
        )
        
        response = model.generate_text(prompt="Hello, Watson!")
        print(f"   ✅ 테스트 성공! 응답: {response}")
        print("\n🎉 모든 설정이 정상입니다.")
        
    except Exception as e:
        print(f"   ❌ [생성 실패] 모델 ID 또는 쿼터(Quota)를 확인하세요.\n   에러: {e}")

if __name__ == "__main__":
    check_connection()