import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from preprocessing.database.pg import get_db_connection

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
app = FastAPI()

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
