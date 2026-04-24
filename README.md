# LLM Wiki — 개인 지식 기반 + Zotero 동기화 시스템

Zotero에서 논문을 자동 추출하고, Obsidian 노트를 통합한 후, Claude를 활용해 구조화된 위키로 합성하는 모듈식 연구 관리 시스템입니다. 연구자를 위해 설계되었습니다.

---

## 🎯 개요

**LLM Wiki**는 다음을 자동화합니다:

1. **추출 (Stage 1)** — Zotero 저장소에서 PDF 텍스트 추출 및 캐싱
2. **미러링 (Stage 0)** — Obsidian 노트를 통합 아카이브에 반영
3. **합성 (Stage 2)** — LLM으로 논문 + 노트를 구조화된 위키로 변환
4. **피드백 (Stage 3)** — 위키 참조를 Zotero 태그와 관련 항목으로 역동기화

**모듈식 설계** — Stage 1만 사용하거나, Stage 2 없이 Zotero 동기화를 스킵할 수 있습니다.

---

## 🚀 빠른 시작

### 1단계: 클론 및 설치

```bash
git clone <repo-url> llm-wiki
cd llm-wiki
pip install -r _scripts/requirements.txt
```

### 2단계: 환경 설정

`config.example.yaml`을 `config.yaml`로 복사하거나 환경변수 설정:

```bash
# Windows PowerShell
$env:ZOTERO_DIR = "$env:USERPROFILE\Zotero"
$env:OBSIDIAN_VAULT = "$env:USERPROFILE\Obsidian"
$env:WIKI_ROOT = "."

# macOS/Linux
export ZOTERO_DIR=~/Zotero
export OBSIDIAN_VAULT=~/Obsidian
export WIKI_ROOT=.
```

### 3단계: Zotero에서 논문 추출

**Zotero는 반드시 닫아야 합니다** (데이터베이스 잠금 때문):

```bash
python _scripts/batch_extract.py
```

→ `papers/{stem}.fulltext.md` 생성 (Zotero의 모든 PDF)

### 4단계: 노트 미러링

```bash
python _scripts/notes_ingest.py
```

→ `notes/{slug}.md` 생성 (설정된 Obsidian 폴더의 모든 .md 파일)

### 5단계 (선택): Claude로 위키 구축

Cowork 에이전트 사용:

```
Cowork에서 Claude에게 묻기:
> 위키를 구축해줘. 각 논문마다 sources/{stem}.md를 만들고,
  관련 개념 페이지를 wiki/{category}/에 추가해.
```

### 6단계 (선택): Zotero에 역동기화

**Zotero는 반드시 열어야 합니다** (로컬 API가 필요):

```bash
python _scripts/zotero_feedback.py
```

→ Zotero 항목에 `wiki:cat/{category}`, `wiki:overview/{topic}` 태그 추가

---

## ⚙️ 작동 원리

### 4단계 파이프라인

| 단계 | 역할 | LLM 토큰 | 시간 |
|------|------|--------|------|
| **0** | Obsidian 노트 → `notes/{slug}.md` 미러링 | 0 | 초 |
| **1** | Zotero PDF → `papers/{stem}.fulltext.md` 추출 | 0 | 분 |
| **2** | 논문+노트 → `sources/`, `wiki/` 합성 (LLM) | ✅ | 가변 |
| **3** | 위키 구조 → Zotero 태그 + 관련 항목 역동기화 | 0 | 초 |

각 단계는 독립적이고 멱등성(idempotent) — 안전하게 재실행 가능합니다.

### 아키텍처

```
Obsidian 볼트          Zotero 라이브러리
      ↓                       ↓
  notes_ingest.py    batch_extract.py
      ↓                       ↓
  notes/{slug}.md    papers/{stem}.fulltext.md
      ↓                       ↓
      └─────────┬─────────────┘
                ↓
           (Claude LLM)
          Stage 2: 위키 구축
                ↓
     sources/{stem}.md
     wiki/{category}/{concept}.md
     wiki/overviews/{topic}.md
                ↓
        zotero_feedback.py
                ↓
         Zotero 태그 + 관련 항목
```

---

## 📁 파일 구조

```
llm-wiki/
├── CLAUDE.md                    # 에이전트 규칙 & 스키마 (필독!)
├── README.md                    # 이 파일 (한글)
├── README_english.md            # 영문 버전
├── config.example.yaml          # 설정 템플릿
├── .gitignore                   # 개인 데이터 제외 규칙
│
├── _scripts/
│   ├── batch_extract.py         # Stage 1: PDF 추출
│   ├── notes_ingest.py          # Stage 0: 노트 미러링
│   ├── zotero_feedback.py       # Stage 3: Zotero 동기화
│   ├── _stem.py                 # 스템(stem) 생성 유틸
│   ├── start_watcher.bat        # 감시 프로세스 시작 (Windows)
│   ├── requirements.txt         # Python 패키지 목록
│   └── SETUP.md                 # 상세 설치 가이드
│
├── _templates/
│   ├── source-template.md       # sources/{stem}.md 템플릿
│   ├── wiki-template.md         # 위키 개념 페이지 템플릿
│   ├── overview-template.md     # 개요 페이지 템플릿
│   └── notes-template.md        # 노트 템플릿
│
├── papers/                      # ← 생성됨: PDF 텍스트 캐시
├── sources/                     # ← 생성됨: LLM 합성 요약
├── wiki/                        # ← 생성됨: 개념 페이지
│   ├── overviews/               # 교차 범주 합성
│   └── {category}/              # 25개 고정 범주
├── notes/                       # ← 생성됨: 미러된 Obsidian 노트
├── documents/                   # Zotero 외 참고 자료 (책, 보고서 등)
└── index.md                     # ← 생성됨: 전체 카탈로그
```

---

## ⚙️ 설정

### 환경변수 방식 (배포 권장)

```bash
# 필수
set ZOTERO_DIR=C:\Users\{username}\Zotero
set OBSIDIAN_VAULT=C:\Users\{username}\Obsidian
set WIKI_ROOT=.

# 선택 (Zotero API)
set ZOTERO_API_BASE=http://127.0.0.1:23119/api/users/0

# 선택 (미러할 Obsidian 폴더 | 구분)
set SCAN_FOLDERS=External Notes|Lab Notes|Tool Notes|Info|Clippings
```

### config.yaml 방식 (개발 권장)

`config.example.yaml`을 복사해서 수정:

```yaml
zotero:
  data_dir: ~/Zotero
  api_base: http://127.0.0.1:23119/api/users/0

obsidian:
  vault_root: ~/Obsidian
  scan_folders:
    - External Notes
    - Lab Notes
    - Tool Notes

wiki:
  root: .
```

환경변수가 config.yaml을 덮어씁니다.

---

## 📖 사용법

### 논문 추출 (Stage 1)

```bash
# 캐시된 것 건너뛰고 증분 처리
python _scripts/batch_extract.py

# 모두 다시 추출
python _scripts/batch_extract.py --force

# 1개 논문만 테스트
python _scripts/batch_extract.py --limit 1

# Zotero 항목 키로 특정 논문만 추출
python _scripts/batch_extract.py --item-key ABCD1234
```

**요구사항:**
- Zotero **반드시 닫기** (데이터베이스 잠김)
- `ZOTERO_DIR` 환경변수 또는 config.yaml

### 노트 미러링 (Stage 0)

```bash
python _scripts/notes_ingest.py
```

**기능:**
- 설정된 Obsidian 폴더 재귀 검색
- 큰 노트 (>32 KB)는 머리+꼬리 자르기 (대역폭 절약)
- 해시 기반 변화 감지 (mtime을 갱신하지 않는 편집도 감지)
- 하루에 여러 번 안전하게 재실행 가능

### Claude로 합성 (Stage 2)

Cowork 에이전트 사용 (Claude 구독 필요):

```
Cowork에서:
> papers/의 모든 논문과 notes/의 모든 노트에서 위키를 구축해줘.
  각 논문마다 CLAUDE.md §7 스키마로 sources/{stem}.md를 만들고,
  관련 개념 페이지를 wiki/{category}/에서 업데이트해.
```

또는 Claude Code:

```bash
claude ask "Build the wiki from papers/ and notes/"
```

### Zotero에 역동기화 (Stage 3)

```bash
# 마지막 실행 이후만 처리
python _scripts/zotero_feedback.py

# 전체 스캔
python _scripts/zotero_feedback.py --full

# 시뮬레이션 (변경사항 표시만)
python _scripts/zotero_feedback.py --dry-run
```

**요구사항:**
- Zotero **반드시 열기** (로컬 API: http://127.0.0.1:23119)
- `ZOTERO_API_BASE` 환경변수 또는 config.yaml

---

## 💡 주요 개념

### Stem (스템)

한 논문의 모든 산출물은 하나의 **stem**을 공유합니다:

```
{첫저자-성}-{연도}-{제목-처음-3개-의미있는-단어}
```

예: `smith-2024-cryo-em-structure`, `bhatia-2025-bioinformatics-framework`

다른 stem을 가진 논문은 저자가 같아도 다른 논문으로 취급합니다.

### 범주 (25개 고정)

위키 개념 페이지는 25개 범주 중 하나에 범위가 정해집니다:

분자생물, 면역학, 생물정보, 유전체, 전사체, 단백질체, 세포생물, 암생물, 신경과학, 미생물, 바이러스, 구조생물, 후생유전, 단일세포, 기계학습, 방법론, 임상, 발달생물, 신호전달, 대사, 신약개발, RNA생물, CRISPR, 리뷰, 진화

새 범주 추가는 승인 필요.

### 콘텐츠 우선순위 계층

위키 페이지 작성 시 콘텐츠는 3단계에서 옵니다:

1. **Tier A (최고):** Obsidian 개인 노트 — 이미 의미 선별됨
2. **Tier B:** Zotero 하이라이트 — 중요한 부분 표시됨
3. **Tier C (대체):** 전체 PDF 텍스트 — 에이전트 해석

에이전트는 **반드시 A와 B를 C보다 우선** 해야 합니다.

---

## 🔧 문제 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| `zotero.sqlite not found` | 잘못된 ZOTERO_DIR | 환경변수 또는 config.yaml 확인 |
| `database is locked` | 추출 중 Zotero 열려 있음 | Zotero 닫고 재시도 |
| `Zotero API unreachable` | 역동기화 중 Zotero 닫혀 있음 | Zotero 열고 재시도 |
| `No module named 'pypdf'` | 패키지 미설치 | `pip install -r _scripts/requirements.txt` |
| `opendataloader-pdf` 실패 | Java PATH에 없음 | OpenJDK 설치 또는 pypdf 폴백 수용 |
| 감시 프로세스 행(hang) | 오래 걸리는 스크립트 | Ctrl+C, `_queue/watcher.log` 확인 |

---

## 📦 공개 배포 체크리스트

**포함:**
- `_scripts/`, `_templates/`, `CLAUDE.md`, `config.example.yaml`, `README.md`, `.gitignore`

**제외:**
- `papers/`, `sources/`, `wiki/`, `notes/`, `documents/` (연구 데이터)
- `config.yaml` (로컬 경로)
- `.env` (인증)
- `_scripts/_queue/` (임시)

`.gitignore` 참조.

---

## 📚 참고

- **CLAUDE.md** — 전체 에이전트 규칙, 스키마, 워크플로우. 사용 전 필독.
- **config.example.yaml** — 모든 설정 옵션 설명.
- **_scripts/SETUP.md** — Windows/macOS/Linux 단계별 설치.
- **_templates/** — sources 및 위키 페이지 템플릿.

---

## 📖 더 알아보기

- `CLAUDE.md` — 시스템 설계 및 에이전트 규칙
- `_scripts/SETUP.md` — 설치 이슈 트러블슈팅
- 각 스크립트 docstring — 사용법 및 매개변수
- 환경변수 또는 `config.yaml` — 경로 및 API 엔드포인트 커스터마이징

---

## 📄 라이선스

이 저장소는 있는 그대로 제공됩니다. 연구에 필요한 대로 수정 및 배포하세요.

---

---

## 📌 참고

저장소에 포함된 `llm-wiki-gist.md`는 안준용 교수님의 gist를 참고한 문서입니다.  
원문: https://gist.github.com/joonan30/cbce305684d079dbe9a3fbaefe4e3959

---

**즐거운 연구 되세요!** 🎓
