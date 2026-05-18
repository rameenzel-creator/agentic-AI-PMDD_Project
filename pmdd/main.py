"""
PMDD FastAPI Backend — Main Application Server
"""

import os
import uuid
import json
import shutil
import asyncio
from pathlib import Path
from typing import AsyncGenerator

# Load .env BEFORE anything else so all agents pick up the key
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from utils.memory import init_db, get_recent_runs, save_run
from utils.pdf_generator import generate_pdf

app = FastAPI(title="PMDD — Pragmatic Meaning Drift Detector", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = Path("uploads")
REPORT_DIR = Path("reports")
STATIC_DIR = Path("frontend")

UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# Initialize database
init_db()

# Mount frontend static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/health")
async def health():
    api_key = os.getenv("NVIDIA_API_KEY", "")
    configured = bool(api_key and "nvapi-" in api_key)
    return {
        "status": "ok",
        "api_configured": configured,
        "key_source": "NVIDIA_API_KEY" if configured else "none",
    }


@app.get("/api/history")
async def get_history():
    runs = get_recent_runs(10)
    return {"runs": runs}


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    keywords: str = Form(default="community, power, change"),
    corpus_name: str = Form(default="Uploaded Corpus"),
):
    """
    Main analysis endpoint.
    Streams SSE progress events back to the client.
    """
    run_id = str(uuid.uuid4())[:8]

    # Save uploaded file
    ext = Path(file.filename).suffix if file.filename else ".txt"
    saved_path = UPLOAD_DIR / f"{run_id}{ext}"
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

    async def event_stream() -> AsyncGenerator[str, None]:
        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        try:
            # Save run to memory
            save_run(run_id, corpus_name, 0)

            # Agent 1
            yield sse("progress", {"agent": 1, "status": "running", "message": "Agent 1: Preprocessing corpus..."})
            await asyncio.sleep(0.1)

            from agents.agent1_preprocessor import run_agent1
            a1 = await asyncio.to_thread(run_agent1, str(saved_path), corpus_name)
            n_segs = len(a1["segments"])
            yield sse("progress", {
                "agent": 1, "status": "done",
                "message": f"Agent 1 complete — {n_segs} segments, {a1['corpus_stats']['total_words']} words",
                "data": a1["corpus_stats"],
            })

            # Agent 2
            yield sse("progress", {"agent": 2, "status": "running", "message": f"Agent 2: Pragmatic analysis (analyzing up to 200 segments)..."})
            from agents.agent2_pragmatic import run_agent2
            a2 = await asyncio.to_thread(run_agent2, a1["segments"], run_id)
            analyzed = sum(1 for s in a2 if s.get("speech_act") not in ("Unknown", "Not Analyzed"))
            corrected = sum(1 for s in a2 if s.get("self_corrected"))
            yield sse("progress", {
                "agent": 2, "status": "done",
                "message": f"Agent 2 complete — {analyzed} segments analyzed, {corrected} self-corrections",
            })

            # Agent 3
            yield sse("progress", {"agent": 3, "status": "running", "message": "Agent 3: Semantic field & register detection..."})
            from agents.agent3_semantic import run_agent3
            a3 = await asyncio.to_thread(run_agent3, a1["segments"], keyword_list, run_id)
            n_sections = len(a3.get("section_summaries", []))
            yield sse("progress", {
                "agent": 3, "status": "done",
                "message": f"Agent 3 complete — {n_sections} sections analyzed",
                "data": a3.get("keyword_drift_scores", {}),
            })

            # Agent 4
            yield sse("progress", {"agent": 4, "status": "running", "message": "Agent 4: Computing corpus statistics..."})
            from agents.agent4_statistics import run_agent4
            a4 = await asyncio.to_thread(run_agent4, a1["segments"])
            yield sse("progress", {
                "agent": 4, "status": "done",
                "message": f"Agent 4 complete — {len(a4.get('collocations', {}))} collocation profiles generated",
                "data": {
                    "hapax_ratio": a4.get("hapax_legomena_ratio"),
                    "total_tokens": a4.get("total_corpus_tokens"),
                },
            })

            # Agent 5
            yield sse("progress", {"agent": 5, "status": "running", "message": "Agent 5: Synthesizing report (Orchestrator)..."})
            from agents.agent5_orchestrator import run_agent5
            report = await asyncio.to_thread(run_agent5, a1, a2, a3, a4, run_id)
            mds = report.get("scores", {}).get("overall_mds", 50)
            yield sse("progress", {
                "agent": 5, "status": "done",
                "message": f"Agent 5 complete — MDS: {mds}/100",
            })

            # Generate PDF
            yield sse("progress", {"agent": 0, "status": "running", "message": "Generating scientific PDF report..."})
            pdf_path = REPORT_DIR / f"PMDD_Report_{run_id}.pdf"
            await asyncio.to_thread(generate_pdf, report, a1, a4, str(pdf_path), corpus_name, run_id)
            yield sse("progress", {"agent": 0, "status": "done", "message": "PDF report ready!"})

            # Final result
            yield sse("complete", {
                "run_id": run_id,
                "report": report,
                "corpus_stats": a1["corpus_stats"],
                "agent4_stats": {
                    "section_stats": a4.get("section_stats", {}),
                    "global_top_30": a4.get("global_top_30", [])[:15],
                    "collocations": a4.get("collocations", {}),
                    "hapax_ratio": a4.get("hapax_legomena_ratio"),
                    "top_bigrams": a4.get("top_bigrams", [])[:10],
                },
                "agent3_data": a3,
                "pdf_url": f"/api/report/{run_id}",
            })

        except Exception as e:
            yield sse("error", {"message": str(e), "run_id": run_id})
        finally:
            # Cleanup uploaded file
            if saved_path.exists():
                saved_path.unlink()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/report/{run_id}")
async def download_report(run_id: str):
    pdf_path = REPORT_DIR / f"PMDD_Report_{run_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"PMDD_Scientific_Report_{run_id}.pdf",
    )
