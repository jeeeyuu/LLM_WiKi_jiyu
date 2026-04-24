# LLM WiKi Jiyu

연구실 내부 공유와 개인 지식 축적을 위해 만든 **LLM 기반 문헌·문서 정리 위키 시스템**입니다.  
논문, 책/매뉴얼 같은 참고 문서, Obsidian 메모를 하나의 저장소로 모으고, 이를 바탕으로 **구조화된 요약(source)**, **개념 위키(concept wiki)**, **오버뷰(overviews)**를 축적하도록 설계되어 있습니다.

핵심 목적은 단순 보관이 아니라, **읽은 내용을 재사용 가능한 지식 구조로 바꾸는 것**입니다.

- markdown viewer는 Obsidian 을 추천합니다.

---

## 이 저장소가 하는 일

이 저장소는 대략 아래 흐름으로 동작합니다.

```text
논문 PDF / 참고 문서 / 외부 노트
        ↓
텍스트 추출 및 정리
        ↓
구조화된 source 문서 생성
        ↓
개념별 wiki 페이지 업데이트
        ↓
overview / graph / index 누적
```

즉, 파일을 모아두는 폴더가 아니라,

- 무엇을 읽었는지 남기고
- 어떤 근거에서 나온 주장인지 추적하고
- 서로 연결되는 개념을 위키처럼 축적하고
- 나중에 다시 질문했을 때 그 축적물을 근거로 답하게 만드는

**연구용 knowledge base**에 가깝습니다.

---

## 핵심 설계 원칙

### 1. Wiki as a single source of truth
에이전트는 웹 검색보다 먼저 이 저장소 안의 내용을 읽도록 설계되어 있습니다.  
즉, 한 번 정리된 내용은 이후 답변과 연결 작업의 **기준 지식(base knowledge)** 가 됩니다.

### 2. 논문과 노트를 같은 지식 그래프 안에 넣기
논문만 따로, 개인 메모만 따로 두지 않고,

- `papers/`
- `documents/`
- `notes/`
- `sources/`
- `wiki/`

를 연결해서 다룹니다.

### 3. 사람이 읽을 수 있는 Markdown 중심
핵심 산출물은 전부 Markdown 기반입니다.  
따라서 Obsidian에서 보기 쉽고, Git으로 추적 가능하며, LLM이 다시 읽어서 확장하기도 쉽습니다.

### 4. 재생성 가능한 구조
텍스트 추출 결과나 LLM이 만든 일부 산출물은 필요 시 다시 만들 수 있도록 설계되어 있습니다.  
즉, 사람이 직접 손으로 정리한 부분과 자동 생성 가능한 부분을 분리합니다.

---

## 폴더 구조

```text
LLM_WiKi_jiyu/
├── CLAUDE.md
├── README.md
├── llm-wiki-gist.md
├── _templates/
├── _scripts/
├── papers/
├── documents/
├── sources/
├── notes/
└── wiki/
    ├── overviews/
    └── {category}/
```

### `CLAUDE.md`
이 저장소의 사실상 **운영 규칙서(agent rulebook)** 입니다.  
에이전트가 어떤 자료를 먼저 읽고, 어떤 형식으로 정리하고, 어떤 근거 표기를 유지해야 하는지를 정의합니다.
- 저장장소가 명시된 부분들은 직접 자신에 맞춰서 수정해주세요.

### `papers/`
Zotero 기반 논문 관련 산출물이 놓이는 위치입니다.

- `papers/{stem}.md` : 사람이 큐레이션한 하이라이트/초록 기반 문서
- `papers/{stem}.fulltext.md` : PDF에서 추출한 전체 텍스트 캐시

원본 논문 PDF 자체는 Zotero storage 쪽에 두고, 이 저장소에는 **텍스트 기반 산출물**을 연결하는 방식입니다.

### `documents/`
논문이 아닌 참고 자료를 넣는 폴더입니다.

예:
- 책 chapter
- manual
- report
- standard
- plain text reference

PDF 문서라면 추출 캐시(`.fulltext.md`)가 생성될 수 있고, `.md`/`.txt` 문서라면 frontmatter를 보강해 바로 downstream으로 넘길 수 있습니다.

### `sources/`
논문이나 문서를 읽고 나서 생성되는 **구조화 요약 문서**입니다.  
실질적으로 “개별 자료 단위의 표준화된 정리본” 역할을 합니다.

보통 다음과 같은 섹션을 포함합니다.

- Thesis
- One-line Summary
- Document Information
- Context
- Key Contributions
- Methodology
- Key Results
- Mechanism / Model
- Strength of Evidence
- Limitations
- Open Questions
- Related Work
- Glossary
- 한국어 요약

### `notes/`
외부 Obsidian 노트를 위키 시스템 안으로 mirror한 폴더입니다.  
에이전트가 이 노트들도 citation 가능한 재료처럼 다룰 수 있게 해 줍니다.

### `wiki/`
자료 개별 요약이 아니라, **개념 중심(concept-level)** 으로 정리되는 페이지들이 들어갑니다.

- `wiki/{category}/` : 주제별 개념 페이지
- `wiki/overviews/` : 여러 source를 종합한 상위 synthesis 페이지

즉, `sources/`가 “개별 문서 단위 정리”라면, `wiki/`는 “지식 구조화 결과물”에 해당합니다.

### `_templates/`
새 문서를 만들 때 사용하는 템플릿 모음입니다.

- `source-template.md`
- `wiki-template.md`
- `overview-template.md`
- `notes-template.md`

형식을 통일하는 데 중요합니다.

### `_scripts/`
자동화 스크립트들이 들어 있는 폴더입니다.  
이 저장소를 실제 파이프라인처럼 굴리게 해 주는 핵심입니다.

---

## 파일 이름 규칙 (`stem`)

논문/문서 관련 산출물은 가능한 한 하나의 공통 stem을 공유하도록 설계되어 있습니다.

기본 형식:

```text
{first-author-lastname}-{year}-{first-3-non-stopword-title-words}
```

예를 들어 하나의 논문에 대해 다음 파일들이 모두 같은 stem을 공유할 수 있습니다.

```text
papers/{stem}.md
papers/{stem}.fulltext.md
sources/{stem}.md
```

이 방식의 장점은,

- 사람이 봐도 어떤 자료인지 바로 알 수 있고
- 스크립트가 pairing하기 쉽고
- 추후 검색/교차연결이 단순해진다는 점입니다.

---

## 자동화 파이프라인

이 저장소는 크게 세 단계로 이해하면 쉽습니다.

### Stage 1. 텍스트 추출 (token-free)
원본 자료에서 LLM이 읽을 수 있는 텍스트 캐시를 만듭니다.

#### 1A. 논문 추출
`_scripts/batch_extract.py`

역할:
- Zotero DB에서 논문 메타데이터 조회
- canonical stem 계산
- PDF 텍스트 추출
- `papers/{stem}.fulltext.md` 생성
- 이미 최신 캐시가 있으면 skip

#### 1B. 비논문 문서 ingest
`_scripts/documents_ingest.py`

역할:
- `documents/` 내부의 `.pdf`, `.md`, `.txt` 처리
- PDF는 `.fulltext.md` 생성
- text 문서는 frontmatter 보강
- unsupported 형식은 로그만 남기고 skip

즉 Stage 1의 목적은 **문서를 LLM이 안정적으로 읽을 수 있는 markdown/text 상태로 바꾸는 것**입니다.

### Stage 2. 지식 구조화 (LLM tokens 사용)
텍스트 캐시를 바탕으로 `sources/`와 `wiki/`를 만듭니다.

핵심 작업:
- source 문서 생성
- concept wiki 업데이트
- overview 보강
- `index.md` 갱신

이 단계가 실제로 “문서를 읽어서 지식으로 바꾸는” 부분입니다.

### Stage 3. Zotero feedback push (token-free)
`_scripts/zotero_feedback.py`

역할:
- 위키/소스 문서의 `zotero_item_key` 확인
- 관련 태그 추가
- linked item을 Zotero Related Items로 푸시

즉, 위키 안에서 정리된 연결관계를 Zotero에도 다시 반영합니다.

---

## 주요 스크립트 설명

### `_scripts/batch_extract.py`
논문 PDF 추출용 스크립트입니다.

주요 특징:
- Zotero storage 기반
- incremental 실행 가능
- `--force`, `--limit`, `--item-key` 지원
- `opendataloader-pdf` 우선, 실패 시 `pypdf` fallback

예시:

```bash
python _scripts/batch_extract.py
python _scripts/batch_extract.py --force
python _scripts/batch_extract.py --limit 5
python _scripts/batch_extract.py --item-key ABCD1234
```

### `_scripts/documents_ingest.py`
논문 외 참고 문서를 `documents/`에서 받아 정리합니다.

예시:

```bash
python _scripts/documents_ingest.py
python _scripts/documents_ingest.py --force
python _scripts/documents_ingest.py --stem pacbio-2024-some-manual
python _scripts/documents_ingest.py --dry-run
```

### `_scripts/notes_ingest.py`
Obsidian 특정 폴더를 스캔하여 `notes/`로 mirror합니다.

기능:
- 외부 note를 first-class citation 재료로 변환
- source hash 기반 drift detection
- 긴 노트는 truncate 처리
- 원본 경로를 frontmatter에 기록

예시:

```bash
python _scripts/notes_ingest.py
```

### `_scripts/watcher.py`
Cowork sandbox와 Windows Python 환경 사이를 연결하는 브리지입니다.

기능:
- `_scripts/_queue/inbox/` 감시
- JSON 명령 수신
- 현재 Python 환경에서 스크립트 실행
- 결과를 `_scripts/_queue/outbox/`에 JSON으로 기록
- heartbeat 유지

즉, “에이전트가 명령을 던지고, 로컬 Python이 실제 작업을 수행하는 구조”를 가능하게 합니다.

### `_scripts/zotero_feedback.py`
위키에서 생성된 cross-reference를 Zotero 쪽 tag / related item으로 다시 밀어 넣습니다.

### `_scripts/build_graph.py`
현재 wiki/source/note 연결관계를 스캔해 graph 표현을 생성합니다.  
지식 그래프가 어떻게 연결되어 있는지 시각적으로 점검할 때 유용합니다.

---

## 권장 사용 흐름

실제로는 아래 순서로 쓰면 됩니다.

### 1. 자료 넣기
- 논문이면 Zotero에 넣기
- 비논문 reference면 `documents/`에 넣기
- 외부 Obsidian note는 지정된 폴더에 작성하기

### 2. token-free 단계 실행
- `notes_ingest.py`
- `batch_extract.py`
- `documents_ingest.py`

### 3. LLM 단계 수행
추출된 텍스트를 기반으로
- `sources/` 생성
- 관련 `wiki/` 갱신
- 필요 시 `overview` 업데이트

### 4. Zotero 연결 반영
- `zotero_feedback.py`

### 5. 그래프/인덱스 확인
- `build_graph.py`
- Obsidian graph view
- `index.md`

---

## 환경 전제

현재 저장소는 범용 멀티플랫폼 툴보다는 **Windows + Obsidian + Zotero + Conda/Miniforge** 조합을 전제로 둔 흔적이 많습니다.

대표적으로 다음 전제를 가집니다.

- Windows 경로 기반 설정
- Zotero local API 사용
- Obsidian vault 위치 고정
- Miniforge 환경 이름(`llmwiki`) 사용
- watcher / bat 파일 중심 실행

따라서 다른 환경에서 바로 복제 실행하려면 경로와 실행 스크립트를 일부 수정해야 할 수 있습니다.

---

## 설치 개요

자세한 설정은 `_scripts/SETUP.md`를 보는 것이 가장 정확합니다.  
대략적으로는 아래 의존성이 필요합니다.

### Python packages

```bash
pypdf
requests
pyyaml
opendataloader-pdf   # optional but recommended
```

### 추가 의존성
- Java (`opendataloader-pdf` 사용 시)
- Zotero desktop
- Obsidian
- Miniforge / conda env

예시:

```bash
conda activate llmwiki
mamba install -c conda-forge pypdf requests openjdk
pip install opendataloader-pdf pyyaml
```

---

## 이 저장소의 장점

### 1. 읽은 것이 누적된다
대부분의 논문 읽기는 그때그때 끝나지만, 이 구조에서는 source와 wiki가 계속 남아서 다음 질문의 기반이 됩니다.

### 2. 논문과 메모가 분리되지 않는다
실제 연구는 논문만으로 굴러가지 않습니다.  
실험 아이디어, 랩 미팅 메모, 해석 메모까지 함께 연결해야 합니다.

### 3. Markdown 기반이라 이식성이 좋다
특정 DB 제품에 종속되지 않고, Git/Obsidian/LLM 어디로도 확장하기 쉽습니다.

### 4. 자동화와 수동 큐레이션의 균형이 있다
- 기계가 잘하는 것: 추출, 정리, 스캐폴딩, 연결
- 사람이 해야 하는 것: 해석, 우선순위, conceptual synthesis

이 역할 분리가 비교적 명확합니다.

---

## 한계와 주의점

### 1. 아직 내부 워크플로우 최적화 성격이 강함
경로, 폴더명, 실행 방식이 개인/랩 환경에 맞춰져 있어 처음 받는 사람에게는 약간 러프할 수 있습니다.

### 2. Stage 2 품질은 프롬프트와 컨텍스트 품질에 좌우됨
텍스트 추출이 잘 되어도, source/wiki 생성 품질은 에이전트 규칙과 입력 품질의 영향을 받습니다.

### 3. PDF 추출 품질은 문서 상태에 따라 달라짐
특히 표, 2-column PDF, 스캔 품질이 낮은 문서는 후처리가 필요할 수 있습니다.

### 4. 완전 자동 지식베이스는 아님
결국 중요한 건 사람이 어떤 개념 페이지를 만들고, 어떤 연결을 유지할지 판단하는 것입니다.

---

## 처음 보는 사람에게 추천하는 시작점

이 저장소를 처음 받았다면 아래 순서로 보는 것을 권장합니다.

1. `CLAUDE.md`  
   → 시스템의 철학과 규칙 이해

2. `_scripts/SETUP.md`  
   → 실제 실행 환경 이해

3. `_templates/source-template.md`  
   → source 문서가 어떤 모양인지 확인

4. `_scripts/batch_extract.py`, `_scripts/documents_ingest.py`, `_scripts/notes_ingest.py`  
   → ingest 흐름 이해

5. `sources/`, `wiki/` 실제 예시  
   → 최종 산출물 확인

---

## 앞으로 확장하면 좋은 점

- `README.md`를 더 짧은 public 버전과 내부 운영 문서로 분리
- `.env` 또는 config 파일 기반 경로 분리
- Stage 2 자동화 인터페이스 명확화
- `index.md` 자동 생성 고도화
- graph / overview 업데이트 규칙 정리
- 샘플 데이터와 예시 source/wiki 페이지 추가

---

## 한 줄 요약

**LLM WiKi Jiyu는 논문, 참고 문서, 개인 노트를 하나의 Markdown 기반 연구 위키로 통합하고, LLM이 그 위에서 누적적으로 지식을 구조화하도록 만든 내부 연구용 knowledge system입니다.**

---

## 참고

저장소에 포함된 `llm-wiki-gist.md`는 안준용 교수님의 gist를 참고한 문서입니다. 원문은 다음 gist입니다: https://gist.github.com/joonan30/cbce305684d079dbe9a3fbaefe4e3959
