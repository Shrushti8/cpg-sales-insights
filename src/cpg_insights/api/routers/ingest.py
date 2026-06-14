"""POST /ingest/upload — accept a CSV file and run it through the live pipeline."""

import tempfile
from pathlib import Path

import duckdb
from fastapi import APIRouter, Depends, HTTPException, UploadFile

from cpg_insights.api.deps import get_conn
from cpg_insights.api.schemas import IngestResponse
from cpg_insights.pipeline.dedupe import dedupe
from cpg_insights.pipeline.extract import extract_pos
from cpg_insights.pipeline.load import load_facts, load_rejected
from cpg_insights.pipeline.transform import transform
from cpg_insights.pipeline.validate import validate

router = APIRouter(prefix="/ingest", tags=["Ingest"])


@router.post("/upload", response_model=IngestResponse)
def ingest_upload(file: UploadFile, conn: duckdb.DuckDBPyConnection = Depends(get_conn)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "upload.csv"
        csv_path.write_bytes(file.file.read())

        try:
            raw = extract_pos(csv_path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not parse CSV: {exc}") from exc

        valid_skus = {r[0] for r in conn.execute("SELECT sku_id FROM dim_product").fetchall()}
        clean, rejected, report = validate(raw, valid_skus)

        if not clean.empty:
            clean = transform(clean)
            clean, _ = dedupe(clean)
            rows_loaded = load_facts(conn, clean)
            load_rejected(conn, rejected)
        else:
            rows_loaded = 0

    return IngestResponse(
        rows_extracted=report.rows_extracted,
        rows_valid=report.rows_valid,
        rows_rejected=report.rows_rejected,
        rows_loaded=rows_loaded,
        rejection_rules=report.rejection_rules,
    )
