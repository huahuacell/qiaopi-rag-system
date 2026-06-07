# 10-Minute Classroom Demo Script

## 0:00-1:00 Project Overview

Show the README, explain this is a local-only Vue + FastAPI scaffold for Qiaopi NLP/RAG work, and note that real models are intentionally not enabled yet.

## 1:00-2:00 Backend Contract

Open `http://localhost:8000/docs`. Show the health endpoint, search endpoints, record endpoints, and generation endpoints.

## 2:00-3:00 Dashboard

Open `http://localhost:5173/`. Explain collection scale, origin/destination distribution, kinship patterns, money amounts, and timeline placeholders.

## 3:00-4:00 Search

Open `/search`, run keyword, semantic, and hybrid searches. Point out that each result has metadata, snippet, score, and evidence.

## 4:00-5:30 Record Detail

Open `/records/CSQP-SFHC-TEXT-001`. Show metadata, original Qiaopi text, normalized text, entity cards, evidence table, and similar records.

## 5:30-7:00 Plain Interpretation

Open `/plain-interpretation`, generate an interpretation for `CSQP-SFHC-TEXT-001`, and explain how the later RAG pipeline will ground generated text in evidence.

## 7:00-8:30 Style Transfer

Open `/style-transfer`, submit a short plain Chinese letter, and show Qiaopi-style output with slot extraction and evidence mapping.

## 8:30-9:30 Analysis

Open `/analysis`, show the word cloud, relation graph, small knowledge graph, and cultural storytelling placeholders.

## 9:30-10:00 Next Steps

Explain backend next steps: Excel ingestion, SQLite, search, FAISS, entity extraction, RAG, and Qwen integration. Explain frontend next steps: refine pages, preserve mock fallback, and test six workflows.

