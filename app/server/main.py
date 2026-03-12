import os
import uuid
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
from typing import Optional
from openai import OpenAI
from preprocessing.database.pg import get_db_connection
from rq import Queue, Worker

EMBEDDING_MODEL = "text-embedding-ada-002"
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o")

EMAIL_SYSTEM_PROMPT = (
    "You are answering a user's question using data from a PROM email thread. "
    "The user's original question is provided as USER_QUESTION. "
    "The retrieved email data is provided below it.\n\n"
    "Guidelines:\n"
    "- Answer the USER_QUESTION directly using the email data.\n"
    "- Weave in relevant details: who was involved, chemicals, processes, "
    "committee considerations, and the outcome.\n"
    "- Keep it concise and natural — you're answering a question, not writing a report.\n"
    "- Use only the provided data. Do not make anything up.\n"
    "- If information is missing, just skip it — don't say \"Not specified\"."
)

PROM_SYSTEM_PROMPT = (
    "You are answering a user's question using data from a past PROM request. "
    "The user's original question is provided as USER_QUESTION. "
    "The retrieved PROM data is provided below it.\n\n"
    "Guidelines:\n"
    "- Answer the USER_QUESTION directly using the PROM data.\n"
    "- Start with something like \"Yes, here's what I know about this\" or similar.\n"
    "- Lay out the relevant information: what was requested, why, chemicals and "
    "processes involved, the process flow, and amounts/forms.\n"
    "- Keep it natural and informative — you're answering a question, not writing a report.\n"
    "- At the end, include a line like: "
    "\"You can find the full PROM form on the Google Drive under '{request_title}'.\"\n"
    "  where {request_title} is replaced with the REQUEST_TITLE from the data.\n"
    "- Use only the provided data. Do not make anything up.\n"
    "- If a field is missing or empty, just skip it."
)


def create_openai_client() -> OpenAI:
    api_key = os.getenv("STANFORD_API_KEY")
    if not api_key:
        raise RuntimeError("Missing STANFORD_API_KEY")

    base_url = "https://aiapi-prod.stanford.edu/v1"
    if os.getenv("STANFORD_API_KEY"):
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


client = create_openai_client()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        clear_uploaded_files_dir()


app = FastAPI(lifespan=lifespan)
redis_memory = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
redis_file_queue = redis.Redis(host="redis", port=6379, db=1)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    text: str


class SearchResult(BaseModel):
    id: int
    title: str
    similarity: float


class SearchResponse(BaseModel):
    results: list[SearchResult]

class UploadRejectedFile(BaseModel):
    filename: str
    reason: str

class UploadFileResponse(BaseModel):
    filename: str
    path: str
    content_type : Optional[str] = None
    size_bytes : int
    status: str

class UploadCounterResetResponse(BaseModel):
    key: str
    value: int


VALID_PROM_UPLOAD_EXTENSIONS = [".pdf", ".docx"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "uploaded_files"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

def clear_uploaded_files_dir() -> None:
    if os.path.isdir(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)



@app.post("/upload/prom", response_model=UploadFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    path: str = Form(...)
) -> UploadFileResponse:
    safe_filename = os.path.basename(file.filename or "upload.bin")
    stem, ext = os.path.splitext(safe_filename)
    unique_suffix = uuid.uuid4().hex[:8]
    stored_filename = f"{stem}__{unique_suffix}{ext}"
    filepath = os.path.join(UPLOAD_DIR, stored_filename)
    #maybe use aiofiles and turn this blocking operation into async
    total_file_bytes = 0
    with open(filepath, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            total_file_bytes += len(chunk)
    await redis_file_queue.rpush("pending_files", filepath)

    return UploadFileResponse(
        filename=file.filename,
        path = path,
        content_type = file.content_type,
        size_bytes = total_file_bytes,
        status = "queued"
    )

@app.post("/upload/emails", response_model=UploadFileResponse)
async def upload_email(
    file: UploadFile = File(...),
    path: str = Form(...)
) -> UploadFileResponse:
    data = await file.read()
    await redis_memory.incr("email_upload_counter")
    return UploadFileResponse(
        filename=file.filename,
        path = path,
        content_type = "email_threads",
        size_bytes = len(data),
        status = "queued"
    )


@app.get("/upload/show-list")
async def show_list():
    data_items = await redis_file_queue.lrange("pending_files", 0, -1)
    return data_items

@app.post("/upload/reset-counter", response_model=UploadCounterResetResponse)
async def reset_upload_counter() -> UploadCounterResetResponse:
    key = "promfile_upload_counter"
    await redis_memory.set(key, 0)
    print(f"{key} set to 0")
    return UploadCounterResetResponse(key=key, value=0)


def embed_query(text: str) -> list[float]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def chat_completion(system_prompt: str, user_payload: str) -> str:
    """Send a system + user message to the LLM and return the response text."""
    print(f"[DEBUG] Sending to chat completion (model={CHAT_MODEL})...")
    completion = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
        temperature=0.2,
    )
    response_text = completion.choices[0].message.content or ""
    print(f"[DEBUG] Chat completion succeeded, response length: {len(response_text)}")
    return response_text.strip() or "No summary returned."




@app.post("/search/emails", response_model=SearchResponse)
def search_emails(request: EmbedRequest) -> SearchResponse:
    """Return the top 5 most similar email threads (llm_context + similarity)."""
    query = request.text.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Text is required")

    query_embedding = embed_query(query)

    con = None
    try:
        con = get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            """
            SELECT
                email_id,
                llm_context,
                1 - (embedding <=> %s::vector) AS similarity
            FROM email_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT 5
            """,
            (query_embedding, query_embedding),
        )
        rows = cursor.fetchall()
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"DB query failed: {error}") from error
    finally:
        if con is not None:
            con.close()

    results = [
        SearchResult(id=row[0], title=row[1] or "No context available", similarity=float(row[2]))
        for row in rows
    ]
    return SearchResponse(results=results)


@app.post("/search/proms", response_model=SearchResponse)
def search_proms(request: EmbedRequest) -> SearchResponse:
    """Return the top 5 most similar PROM requests (title + similarity only)."""
    query = request.text.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Text is required")

    query_embedding = embed_query(query)

    con = None
    try:
        con = get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            """
            SELECT
                prom_id,
                request_title,
                1 - (request_embedding <=> %s::vector) AS similarity
            FROM prom_embeddings
            ORDER BY request_embedding <=> %s::vector
            LIMIT 5
            """,
            (query_embedding, query_embedding),
        )
        rows = cursor.fetchall()
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"DB query failed: {error}") from error
    finally:
        if con is not None:
            con.close()

    results = [
        SearchResult(id=row[0], title=row[1] or "Untitled Request", similarity=float(row[2]))
        for row in rows
    ]
    return SearchResponse(results=results)


@app.post("/embed/emails", response_model=EmbedResponse)
def embed_emails(request: EmbedRequest) -> EmbedResponse:
    query = request.text.strip()
    print(f"[DEBUG][emails] Received query: '{query}'")
    if not query:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        print("[DEBUG][emails] Embedding query...")
        query_embedding = embed_query(query)
        print(f"[DEBUG][emails] Embedding succeeded, dim={len(query_embedding)}")
    except Exception as error:
        print(f"[ERROR][emails] Embedding failed: {error}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {error}") from error

    con = None
    try:
        print("[DEBUG][emails] Connecting to database...")
        con = get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            """
            SELECT
                date,
                requestor,
                filename,
                prom_approval,
                prom_considerations,
                chemicals,
                processes,
                raw_thread,
                1 - (embedding <=> %s::vector) AS similarity
            FROM email_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT 1
            """,
            (query_embedding, query_embedding),
        )
        row = cursor.fetchone()
        print(f"[DEBUG][emails] DB query done. Row found: {row is not None}")
    except Exception as error:
        print(f"[ERROR][emails] DB query failed: {error}")
        raise HTTPException(status_code=500, detail=f"DB query failed: {error}") from error
    finally:
        if con is not None:
            con.close()

    if row is None:
        return EmbedResponse(text="No relevant emails found.")

    (
        date, requestor, filename, prom_approval, prom_considerations,
        chemicals, processes, raw_thread, similarity,
    ) = row

    print(f"[DEBUG][emails] Best match: date={date}, requestor={requestor}, similarity={similarity:.4f}")

    user_payload = (
        f"USER_QUESTION: {query}\n\n"
        "RAW_THREAD:\n"
        f"{raw_thread}\n\n"
        f"PROM_APPROVAL: {prom_approval}\n"
        f"PROM_CONSIDERATIONS: {prom_considerations}\n"
        f"CHEMICALS: {chemicals}\n"
        f"PROCESSES: {processes}\n"
    )

    try:
        response_text = chat_completion(EMAIL_SYSTEM_PROMPT, user_payload)
    except Exception as error:
        print(f"[ERROR][emails] Chat completion failed: {error}")
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {error}") from error

    return EmbedResponse(text=response_text)



@app.post("/embed/proms", response_model=EmbedResponse)
def embed_proms(request: EmbedRequest) -> EmbedResponse:
    query = request.text.strip()
    print(f"[DEBUG][proms] Received query: '{query}'")
    if not query:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        print("[DEBUG][proms] Embedding query...")
        query_embedding = embed_query(query)
        print(f"[DEBUG][proms] Embedding succeeded, dim={len(query_embedding)}")
    except Exception as error:
        print(f"[ERROR][proms] Embedding failed: {error}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {error}") from error

    con = None
    try:
        print("[DEBUG][proms] Connecting to database...")
        con = get_db_connection()
        cursor = con.cursor()
        cursor.execute(
            """
            SELECT
                request_title,
                chemicals_and_processes,
                request_reason,
                process_flow,
                amount_and_form,
                1 - (request_embedding <=> %s::vector) AS similarity
            FROM prom_embeddings
            ORDER BY request_embedding <=> %s::vector
            LIMIT 1
            """,
            (query_embedding, query_embedding),
        )
        row = cursor.fetchone()
        print(f"[DEBUG][proms] DB query done. Row found: {row is not None}")
    except Exception as error:
        print(f"[ERROR][proms] DB query failed: {error}")
        raise HTTPException(status_code=500, detail=f"DB query failed: {error}") from error
    finally:
        if con is not None:
            con.close()

    if row is None:
        return EmbedResponse(text="No relevant PROM requests found.")

    (
        request_title, chemicals_and_processes, request_reason,
        process_flow, amount_and_form, similarity,
    ) = row

    print(f"[DEBUG][proms] Best match: title={request_title}, similarity={similarity:.4f}")

    user_payload = (
        f"USER_QUESTION: {query}\n\n"
        f"REQUEST_TITLE: {request_title}\n"
        f"CHEMICALS_AND_PROCESSES: {chemicals_and_processes}\n"
        f"REQUEST_REASON: {request_reason}\n"
        f"PROCESS_FLOW: {process_flow}\n"
        f"AMOUNT_AND_FORM: {amount_and_form}\n"
    )

    try:
        response_text = chat_completion(PROM_SYSTEM_PROMPT, user_payload)
    except Exception as error:
        print(f"[ERROR][proms] Chat completion failed: {error}")
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {error}") from error

    return EmbedResponse(text=response_text)
