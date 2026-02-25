# Qwen Voice Studio 🎙️

Voice Studio는 **Qwen3-TTS 모델**의 Zero-Shot 보이스 클로닝 기능을 웹 브라우저에서 쉽고 직관적으로 사용할 수 있도록 만든 로컬 전용 웹 UI 애플리케이션입니다.

원하는 사람의 음성(레퍼런스) 파일 1개와 대본만 업로드하면, 해당 목소리 톤과 말투를 복제하여 새로운 텍스트를 읽어주는 음성 생성이 가능합니다.

## ✨ 기능 특징
- **로컬 구동**: 외부 서버로 데이터를 전송하지 않고 사용자의 PC(Mac MPS 또는 CPU) 환경에서 100% 로컬로 구동됩니다. 개인정보나 음성이 유출될 우려가 없습니다.
- **직관적인 UI**: 파일 업로드, 대본 입력, 생성하기 버튼의 매우 단순한 인터페이스를 갖추고 있습니다.
- **자동 오디오 정규화**: 입력된 레퍼런스 음성의 볼륨을 자동으로 증폭하고 `.wav`로 변환하여 퀄리티 높은 생성물을 보장합니다.

## 🚀 설치 및 초기 세팅 방법

초기 세팅은 딱 한 번만 수행하면 됩니다. 맥(Mac) 환경 기준입니다.

### 1단계: 가상 환경 설정 및 패키지 설치
터미널을 열고 프로젝트 폴더(`qwen_voice_studio`) 안에서 아래 명령어를 순서대로 입력하세요.

```bash
# 1. 가상 환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 2. 필수 라이브러리 전체 설치
pip install -r requirements.txt
```

> **참고**: 맥 환경에서 오디오 변환을 위해 `ffmpeg`가 운영체제에 설치되어 있어야 합니다. 터미널에서 홈브류(Homebrew)를 통해 설치해 주세요. (`brew install ffmpeg`)

### 2단계: 필수 모델 다운로드 (Qwen3-TTS)
이 프로젝트는 초대형 AI 가중치(약 3.8GB) 파일이 필요합니다. 
`huggingface-cli`를 사용하여 프로젝트 폴더 안에 필요한 파일들을 자동으로 다운로드합니다. 이 위치에서 아래 명령어를 차례대로 복사해서 실행하세요.

```bash
# 초고속 다운로드 모드 활성화 환경변수
export HF_HUB_ENABLE_HF_TRANSFER=1

# 기존 코드와의 충돌을 막기 위해 파이썬(.py)과 잡다한 파일(마크다운 등)을 제외하고
# 현 위치(.)에 핵심 모델 파일과 설정 파일들만 다운로드합니다.
huggingface-cli download Qwen/Qwen3-TTS-12Hz-1.7B-Base \
  --local-dir . \
  --exclude "*.py" "*.md" ".git*"
```
*(↑ 위 명령어를 실행하면 `model.safetensors`, `config.json`, `vocab.json` 및 `speech_tokenizer/` 폴더 등이 알아서 다운로드됩니다. 다운로드에 1~5분 정도 소요될 수 있습니다.)*

---

## 🏃‍♂️ 사용 및 실행 방법

### 1단계: 웹 서버 실행
모든 준비가 완료되었다면 아래 명령어로 FastAPI 웹 서버를 띄워 스튜디오를 켤 수 있습니다. (항상 가상환경 `venv`가 활성화된 상태여야 합니다)

```bash
python app.py
```

- 터미널에 `[*] Model loaded successfully on mps!` 라는 문구가 뜨면 성공입니다.
- 브라우저를 열고 `http://localhost:8000` 에 접속하여 서비스를 이용해 보세요 🎉.

---

### * (선택) CLI 모드로 실행하기 
직접 코드를 타이핑하며 빠르게 터미널에서 테스트하려면 아래 명령어를 사용하세요.
```bash
python cli.py
```
> 주의사항: CLI로 실행하기 전에 `cli.py` 파일 내부의 `REFERENCE_AUDIO` 경로와 `REFERENCE_TEXT`를 본인 환경에 맞게 직접 수정하신 후 실행하셔야 합니다!
