from app.generation.qwen_client import QwenClient


def run_rag_placeholder(question: str, evidence: list) -> dict:
    generated_text = QwenClient().generate(question)
    return {
        "generated_text": generated_text,
        "evidence": evidence,
        "message": "RAG retrieval and generation are placeholders in this phase.",
    }

