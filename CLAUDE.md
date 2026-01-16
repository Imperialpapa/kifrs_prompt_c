# K-IFRS 1019 DBO Validation System - 개발 지침

## 코딩 원칙

### 하드코딩 금지
- 설정값, 버전, URL, API 키 등은 **절대 하드코딩하지 않음**
- 환경변수(.env) 또는 config.py에서 읽어서 사용
- 상수는 파일 상단 또는 별도 constants.py에 정의

### 예시
```python
# ❌ 잘못된 예
ai_model_version = "claude-sonnet-4-20250514"

# ✅ 올바른 예
import os
ai_model_version = os.getenv("AI_MODEL_VERSION", "local-parser")
```

## 프로젝트 구조

- `backend/`: FastAPI 백엔드
- `index.html`: 프론트엔드 (Alpine.js)
- `backend/.env`: 환경변수 설정

## 주요 설정 파일

- `.env`: 환경변수 (API 키, DB 연결 등)
- `config.py`: 애플리케이션 설정

## AI 해석 엔진

- **로컬 파서** (기본값): 정규식 기반, 빠르고 정확
- **Cloud AI** (선택): OpenAI, Anthropic, Gemini - API 키 필요

## 테스트

변경 후 반드시 테스트:
1. 규칙 파일 업로드
2. 데이터 파일 검증
3. 결과 확인
