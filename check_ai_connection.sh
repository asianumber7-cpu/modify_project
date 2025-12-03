#!/bin/bash

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Modify AI 서비스 연결 진단을 시작합니다...${NC}"

# 1. 파일 복사 (로컬 -> 컨테이너)
# ai-service 폴더에 check_watsonx.py가 있다고 가정하고 컨테이너로 복사
if [ -f "./ai-service/check_watsonx.py" ]; then
    echo "📂 진단 스크립트를 컨테이너로 복사합니다..."
    # 윈도우 Git Bash 경로 변환 방지를 위해 타겟 경로 앞에 // 사용 (선택적)
    docker cp ./ai-service/check_watsonx.py modify-ai-api://app/check_watsonx.py
else
    echo -e "${RED}❌ 'ai-service/check_watsonx.py' 파일을 찾을 수 없습니다. 파일을 생성했는지 확인해주세요.${NC}"
    exit 1
fi

# 2. 스크립트 실행
echo "🚀 컨테이너 내부에서 진단 스크립트를 실행합니다..."
echo "---------------------------------------------------------"

# [FIX] Git Bash(MinGW)에서 리눅스 절대 경로(/app/...)가 윈도우 경로로 자동 변환되는 것을 막기 위해
# 맨 앞에 슬래시를 하나 더 붙여 //app/... 으로 사용합니다. (리눅스/맥에서도 동작함)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # 윈도우 환경 (winpty 추가 권장, 경로는 //app 사용)
    winpty docker exec -it modify-ai-api python //app/check_watsonx.py
else
    # 리눅스/맥 환경
    docker exec -it modify-ai-api python /app/check_watsonx.py
fi

echo "---------------------------------------------------------"
echo -e "${GREEN}진단이 완료되었습니다.${NC}"