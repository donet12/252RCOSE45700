from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


PROMPT_TEMPLATE = """
당신은 프라이빗 뱅킹·기업 금융팀을 돕는 상주 금융 컨설턴트입니다.

다음 규칙을 따라 답변하세요:
- 제공된 문맥을 적극적으로 활용하여 질문에 구체적이고 실용적인 답변을 제공하세요.
- 문맥에 관련 정보가 있으면 반드시 활용하고, 문맥을 바탕으로 논리적으로 추론하여 답변하세요.
- 문맥에 직접적인 답이 없어도 관련된 정보를 연결하여 유용한 답변을 제공하세요.
- "요즘", "최근", "현재" 같은 시간 표현이 있으면 문맥에서 가장 최신 정보를 찾아 답변하세요.
- 문맥에 금융규제, 정책, 동향 관련 내용이 있으면 그것을 바탕으로 답변하세요.
- 규제/리스크 지표 등 수치는 문맥에서 확인된 값만 사용하세요.
- 본문에서 참조한 문단 옆에는 [출처번호]를 붙이세요.
- 답변은 명확하고 실용적이며, 사용자가 이해하기 쉽게 작성하세요.
- 이전 대화 내용을 참고하여 맥락에 맞는 답변을 제공하세요.
- 절대 "정보를 찾을 수 없습니다"라고만 답변하지 말고, 문맥에서 찾은 관련 정보를 바탕으로 최선을 다해 답변하세요.

{conversation_history}

질문: {question}

문맥:
{context}
"""


@dataclass
class RAGConfig:
    """RAG 챗봇 구성 옵션."""

    data_dir: Path
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # 로컬 임베딩 모델
    llm_model: str = "gpt-4o-mini"  # OpenAI LLM 모델
    chunk_size: int = 500
    chunk_overlap: int = 80
    top_k: int = 5
    temperature: float = 0.1
    openai_api_key: str | None = None


class RAGChatbot:
    """LangChain 기반 금융 전문 RAG 챗봇."""

    def __init__(self, config: RAGConfig) -> None:
        self.config = config
        self.documents = self._load_documents()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        # 로컬 임베딩 모델 사용 (OpenAI API 할당량 문제 해결)
        self.embedding = HuggingFaceEmbeddings(
            model_name=self.config.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.vector_store = self._build_vector_store()
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": config.top_k})
        self.llm = self._build_llm()
        self.prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)

    def ask(self, question: str, conversation_history: List[Dict[str, str]] | None = None) -> Dict[str, List[str] | str]:
        """질문에 답하고 출처를 포함한다."""
        retrieved_docs = self.retriever.get_relevant_documents(question)

        if not retrieved_docs:
            return {
                "answer": "관련 문서를 찾지 못했습니다. 데이터 소스를 추가해 주세요.",
                "sources": [],
            }

        formatted_context = self._format_context(retrieved_docs)
        
        # 대화 기록 포맷팅
        conversation_text = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history[-5:]:  # 최근 5개 대화만 사용
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    history_lines.append(f"사용자: {content}")
                elif role == "assistant":
                    history_lines.append(f"어시스턴트: {content}")
            if history_lines:
                conversation_text = "이전 대화:\n" + "\n".join(history_lines) + "\n\n"
        
        model_input = self.prompt.format(
            context=formatted_context,
            question=question,
            conversation_history=conversation_text
        )
        answer_message = self.llm.invoke(model_input)
        answer = getattr(answer_message, "content", str(answer_message)).strip()
        sources = self._collect_sources(retrieved_docs)

        # 답변에 이미 참고 문서가 포함되어 있는지 확인
        if "참고 문서" not in answer and "참고" not in answer:
            answer_with_sources = f"{answer}\n\n참고 문서:\n" + "\n".join(
                f"- {source}" for source in sources
            )
        else:
            # 이미 포함되어 있으면 그대로 사용
            answer_with_sources = answer

        return {"answer": answer_with_sources, "sources": sources}

    def _load_documents(self) -> List[Document]:
        """데이터 디렉토리에서 문서를 불러온다."""
        if not self.config.data_dir.exists():
            raise FileNotFoundError(f"데이터 디렉토리를 찾을 수 없습니다: {self.config.data_dir}")

        documents: List[Document] = []
        for pattern in ("*.md", "*.txt"):
            for path in sorted(self.config.data_dir.glob(pattern)):
                loader = TextLoader(str(path), encoding="utf-8")
                loaded_docs = loader.load()
                for doc in loaded_docs:
                    doc.metadata["source"] = path.name
                documents.extend(loaded_docs)

        if len({doc.metadata.get("source") for doc in documents}) < 2:
            raise ValueError("최소 두 개 이상의 데이터 소스가 필요합니다.")

        return documents

    def _build_vector_store(self) -> FAISS:
        """문서 임베딩 후 벡터스토어를 구축한다."""
        chunks = self.text_splitter.split_documents(self.documents)
        return FAISS.from_documents(chunks, self.embedding)

    def _build_llm(self) -> ChatOpenAI:
        """OpenAI 채팅 모델을 구성한다."""
        return ChatOpenAI(
            model=self.config.llm_model,
            temperature=self.config.temperature,
            api_key=self.config.openai_api_key,
            max_tokens=600,
        )

    @staticmethod
    def _format_context(documents: List[Document]) -> str:
        """Retrieval 결과를 번호와 함께 문자열로 변환한다."""
        formatted_chunks = []
        for idx, doc in enumerate(documents, start=1):
            source = doc.metadata.get("source", f"document_{idx}")
            formatted_chunks.append(f"[출처{idx}: {source}]\n{doc.page_content}")
        return "\n\n".join(formatted_chunks)

    @staticmethod
    def _collect_sources(documents: List[Document]) -> List[str]:
        """사용된 문서 출처를 중복 없이 정리한다."""
        seen = set()
        sources: List[str] = []
        for doc in documents:
            source = doc.metadata.get("source", "unknown")
            if source not in seen:
                seen.add(source)
                sources.append(source)
        return sources

