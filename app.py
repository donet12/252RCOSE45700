from __future__ import annotations

import argparse
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

from src.rag_chatbot import RAGChatbot, RAGConfig

load_dotenv()

app = Flask(__name__)

# 전역 챗봇 인스턴스
chatbot: RAGChatbot | None = None


def init_chatbot(
    data_dir: Path,
    embedding_model: str,
    llm_model: str,
    top_k: int,
    temperature: float,
    openai_api_key: str | None,
) -> None:
    """챗봇을 초기화한다."""
    global chatbot
    config = RAGConfig(
        data_dir=data_dir,
        embedding_model=embedding_model,
        llm_model=llm_model,
        top_k=top_k,
        temperature=temperature,
        openai_api_key=openai_api_key or os.getenv("OPENAI_API_KEY"),
    )
    chatbot = RAGChatbot(config)


@app.route("/")
def index() -> str:
    """메인 페이지."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat() -> dict:
    """채팅 API 엔드포인트."""
    if chatbot is None:
        return jsonify({"error": "챗봇이 초기화되지 않았습니다."}), 500

    data = request.get_json()
    question = data.get("question", "").strip()
    conversation_history = data.get("conversation_history", [])

    if not question:
        return jsonify({"error": "질문을 입력해주세요."}), 400

    try:
        response = chatbot.ask(question, conversation_history=conversation_history)
        return jsonify(
            {
                "answer": response["answer"],
                "sources": response["sources"],
            }
        )
    except Exception as e:
        return jsonify({"error": f"오류가 발생했습니다: {str(e)}"}), 500


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="금융 전문가 RAG 챗봇 (웹 인터페이스)")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="문서가 위치한 디렉토리 경로",
    )
    parser.add_argument(
        "--embedding-model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="로컬 임베딩 모델 이름 (기본: sentence-transformers/all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "--llm-model",
        default="gpt-4o-mini",
        help="OpenAI 채팅 모델 이름",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="검색 시 사용할 문서 개수",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="LLM 생성 온도",
    )
    parser.add_argument(
        "--openai-api-key",
        default=None,
        help="필요 시 명시적으로 지정할 OpenAI API 키 (기본은 환경 변수)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="서버 호스트 (기본: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="서버 포트 (기본: 5000)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("챗봇 초기화 중...")
    init_chatbot(
        data_dir=args.data_dir,
        embedding_model=args.embedding_model,
        llm_model=args.llm_model,
        top_k=args.top_k,
        temperature=args.temperature,
        openai_api_key=args.openai_api_key,
    )
    print("초기화 완료!")

    print(f"\n웹 서버 시작: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
