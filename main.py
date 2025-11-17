import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Config, Document

app = FastAPI(title="DeFi Moderation AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigResponse(BaseModel):
    id: str
    bot_token: Optional[str]
    gemini_api_key: Optional[str]
    notes: Optional[str]


class DocumentResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: Optional[List[str]]


@app.get("/")
def read_root():
    return {"message": "DeFi Moderation Assistant Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response


@app.get("/api/config", response_model=List[ConfigResponse])
def list_configs():
    docs = get_documents("config")
    results: List[ConfigResponse] = []
    for d in docs:
        results.append(ConfigResponse(
            id=str(d.get("_id")),
            bot_token=d.get("bot_token"),
            gemini_api_key=d.get("gemini_api_key"),
            notes=d.get("notes")
        ))
    return results


@app.post("/api/config", response_model=str)
def create_or_update_config(cfg: Config):
    # store as a new config document; in the future could be upsert by some key
    inserted_id = create_document("config", cfg)
    return inserted_id


@app.get("/api/docs", response_model=List[DocumentResponse])
def list_documents():
    docs = get_documents("document")
    results: List[DocumentResponse] = []
    for d in docs:
        results.append(DocumentResponse(
            id=str(d.get("_id")),
            title=d.get("title", "Untitled"),
            content=d.get("content", ""),
            tags=d.get("tags")
        ))
    return results


@app.post("/api/docs", response_model=str)
def create_document_endpoint(doc: Document):
    inserted_id = create_document("document", doc)
    return inserted_id


# Simple analyze endpoint using Gemini placeholder logic
class AnalyzeRequest(BaseModel):
    query: str

class AnalyzeResponse(BaseModel):
    answer: str
    used_docs: List[str] = []


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    # For now: simple heuristic using documents; in a real implementation, call Gemini API with cfg.gemini_api_key
    docs = get_documents("document")
    matched = []
    for d in docs:
        if req.query.lower() in (d.get("content", "") + " " + d.get("title", "")).lower():
            matched.append(d)
    summary = "I found relevant information in your uploaded docs." if matched else "No direct match in docs; consider adding more context."
    used_titles = [d.get("title", "Untitled") for d in matched][:5]
    answer = f"Summary: {summary}"
    if used_titles:
        answer += " | Sources: " + ", ".join(used_titles)
    return AnalyzeResponse(answer=answer, used_docs=used_titles)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
