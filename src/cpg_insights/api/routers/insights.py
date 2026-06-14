"""GET /insights/summary and POST /chat."""

import duckdb
from fastapi import APIRouter, Depends

from cpg_insights.api.deps import get_conn, get_llm
from cpg_insights.api.schemas import ChatRequest, ChatResponse, InsightsSummaryResponse
from cpg_insights.llm.base import LLMProvider
from cpg_insights.llm.insights import answer_question, get_summary

router = APIRouter(tags=["Insights"])


@router.get("/insights/summary", response_model=InsightsSummaryResponse)
def insights_summary(
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
    llm: LLMProvider = Depends(get_llm),
):
    return InsightsSummaryResponse(summary=get_summary(conn, llm))


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_conn),
    llm: LLMProvider = Depends(get_llm),
):
    answer = answer_question(req.question, conn, llm)
    return ChatResponse(question=req.question, answer=answer)
