## FinSage Analyst: 금융 전문가 RAG 챗봇

금융감독 보고서·투자자 가이드·은행 정책 등을 인덱싱해 “요즘 금융규제 흐름은?”, “포트폴리오 리밸런싱 기준은?” 같은 전문 질문에 근거 문서와 함께 답변합니다. LangChain RAG + OpenAI LLM + Flask 웹 UI로 구성되며, 로컬 임베딩을 사용해 비용을 최소화하고 최근 대화 맥락을 기억합니다.

---

### 핵심 기능
- **규제/정책 문서 검색**: `data/` 폴더의 `.md/.txt` 문서를 청크 단위로 임베딩 후 FAISS로 검색
- **출처 기반 답변**: 답변 본문에 `[출처번호]` 표기, 하단에 `참고 문서` 목록 자동 출력
- **대화 맥락 기억**: 클라이언트 단에서 최근 5개의 Q/A를 전송해 후속 질문에 맥락 반영
- **PDF 변환 툴 내장**: `convert_pdf.py`로 대용량 정책 PDF를 Markdown으로 전처리

---

### 설치 및 실행

1. **의존성 설치**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **OpenAI API 키 설정**
   ```bash
   export OPENAI_API_KEY=sk-xxxx
   ```
3. **서버 실행**
   ```bash
   python app.py --data-dir data --top-k 5
   ```
   브라우저에서 `http://127.0.0.1:5000`으로 접속합니다.

**주요 옵션**  
`--embedding-model`, `--llm-model`, `--top-k`, `--temperature`, `--openai-api-key`, `--host`, `--port`

---

### 데이터 준비 플로우

1. **PDF 확보**: 금융감독원, 금융투자협회, 한국은행 등에서 규제/정책 PDF 다운로드  
2. **Markdown 변환**
   ```bash
   python convert_pdf.py "data/한국은행 통화신용정책보고서 2024.pdf" \
     -o data/bok_monetary_policy_2024.md
   ```
3. **샘플 유지**: `data/`에 최소 2개의 `.md` 파일을 유지해야 인덱싱이 진행됩니다.  
   원본 PDF는 `.gitignore`에 포함하고, 변환본만 버전에 포함하세요.

**포함된 예시 문서**
- `wealth_portfolio_playbook.md`
- `bank_risk_controls.md`
- `2024년 금융규제 운영규정 실태평가 최종 보고서.md`
- `[요약] 2024 한국 부자보고서.md`
- `별첨자료_금융광고규제가이드라인.md`
- `지속가능금융의 의의.md`

---

### 작동 방식

1. 서버 실행 시 `data/` 내부 문서를 로딩 → 청크 분할 → `all-MiniLM-L6-v2` 임베딩 생성  
2. FAISS 벡터스토어를 메모리에 생성 (디스크 저장 X)  
3. 질문 수신 → 최근 대화와 문맥을 PromptTemplate에 주입 → OpenAI LLM 호출  
4. `[출처번호]`가 삽입된 답변 + `참고 문서` 리스트 반환  
5. 프론트엔드는 대화 기록을 메모리에 저장해 후속 질문 시 서버로 함께 전송

---

### 프로젝트 구조
```
.
├── app.py                 # Flask 서버 & REST API
├── templates/
│   └── index.html        # 웹 채팅 UI + 대화 기록 관리
├── convert_pdf.py        # PDF → Markdown 변환 스크립트
├── data/                 # 변환된 문서(.md)와 원본 PDF(ignored)
├── src/
│   └── rag_chatbot.py   # LangChain RAG 파이프라인
├── requirements.txt
└── README.md
```

---

### 웹 인터페이스 사용법
1. 서버 실행 → `http://127.0.0.1:5000` 접속
2. 금융/규제/투자 질문 입력 (예: “요즘 금융규제 트렌드는?”)
3. 답변 + 참고 문서 확인
4. 동일 세션에서 이전 질문을 기억하므로 후속 질문도 자연스럽게 이어짐
5. 새로고침 시 대화 기록 초기화

---

### GitHub 업로드 팁
- 변환된 `.md`만 포함 (PDF는 `.gitignore` 처리)
- `data/`에 최소 2개의 샘플 `.md` 유지
- `.env`, `.venv`, `data/*.pdf` 등 민감/대용량 파일 제외
- README에 문서 출처/다운로드 링크를 명시하면 과제 평가에 유리

---

### FAQ
- **대화 기록 저장 위치?**  
  브라우저 메모리 (새로고침 시 초기화).

- **벡터스토어는 어디 저장?**  
  메모리에만 존재합니다. 필요 시 `FAISS.save_local()`을 추가하세요.

- **PDF 변환 방법?**  
  `python convert_pdf.py data/보고서.pdf -o data/보고서.md`

- **OpenAI 크레딧 부족 시?**  
  답변 생성이 불가하므로 크레딧을 충전하거나 로컬 LLM을 추가로 구성해야 합니다.


