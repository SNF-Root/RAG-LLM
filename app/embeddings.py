#vector db going to have date, requestor, requestor_full_name, email_filename, msg_start, msg_end, PROM_info, embeddings(PROM_info) 
import psycopg2
from psycopg2.extras import execute_values
import os
from promTothread import extract_key_from_pdf
from sqdb import get_ids_from_keys, get_email_by_msgid, get_db_connection
import json
import hashlib
from typing import Optional, List, Dict
from openai import OpenAI
import numpy as np


from dotenv import load_dotenv
load_dotenv()



BANNER = r"""
/******************************************************************************\
*                                                                              *
*                         N E X T   E M A I L   T H R E A D                    *
*                                                                              *
\******************************************************************************/
"""


# TABLE_NAME = "prom_embeddings"
# EMBEDDING_MODEL = "text-embedding-3-small"
# EMBEDDING_DIM = 1536

# def init_embeddings_table():
#     con = get_db_connection()
#     cursor = con.cursor()

#     # Enable pgvector extension (required before using vector type)
#     cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
#     cursor.execute(f"""
#     CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
#         doc_id TEXT PRIMARY KEY,
#         date TEXT NOT NULL,
#         requestor TEXT NOT NULL,
#         requestor_full_name TEXT NOT NULL,
#         email_filename TEXT NOT NULL,
#         msg_start INTEGER NOT NULL,
#         msg_end INTEGER NOT NULL,
#         prom_info TEXT NOT NULL,
#         embedding vector({EMBEDDING_DIM})
#     )
#     """)

#     cursor.execute(f"""
#         CREATE INDEX IF NOT EXISTS idx on {TABLE_NAME}
#         USING hnsw (embedding vector_cosine_ops)
#     """)

#     con.commit()
#     con.close()


def embed(query: str, client: OpenAI):
    response = client.embeddings.create(
        model = EMBEDDING_MODEL,
        input=query
    )

    return response.data[0].embedding


def insert_prom_record(doc_id, date, requestor, requestor_name, email_filename, msg_start, msg_end, prom_info, embedding) -> bool:
    con = get_db_connection()
    cursor = con.cursor()

    cursor.execute(f"SELECT doc_id FROM {TABLE_NAME} WHERE doc_id = %s", (doc_id,))
    if cursor.fetchone():
        print(f"DOC ALREADY PROCESSED AND INSIDE {TABLE_NAME}")
        return False
    
    cursor.execute(f"""
        INSERT INTO {TABLE_NAME} 
        (doc_id, date, requestor, requestor_full_name, email_filename, msg_start, msg_end, prom_info, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(doc_id) DO NOTHING
    """, (
        doc_id,
        date,
        requestor,
        requestor_name,
        email_filename,
        msg_start,
        msg_end,
        prom_info,
        str(embedding)
    ))

    con.commit()
    con.close()
    return True


def search_prom(query):
    n_results = 1
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    query_embedding = embed(query, client)

    con = get_db_connection()
    cursor = con.cursor()

    cursor.execute(f"""
        SELECT
            doc_id,
            date,
            requestor,
            requestor_full_name,
            email_filename,
            msg_start,
            msg_end,
            prom_info,
            1 - (embedding <=> %s::vector) as cosine_similarity
        FROM {TABLE_NAME}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (str(query_embedding), str(query_embedding), n_results))

    row = cursor.fetchone()
    con.close()

    if row is None:
        return []
    
    hits = [{
            "id": row[0],
            "distance": 1 - float(row[8]),  # Convert similarity back to distance
            "date": row[1],
            "requestor": row[2],
            "requestor_full_name": row[3],
            "email_filename": row[4],
            "msg_start": row[5],
            "msg_end": row[6],
            "prom_info": row[7],
    }]

    return hits

if __name__ == "__main__":
    init_embeddings_table()
    
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    
    files = ["ashutoshPROM.pdf", "helenaPROM.pdf"]
    path = "/app/files"
    
    for file in files:
        pdf_path = os.path.join(path, file)
        result = extract_key_from_pdf(pdf_path)
        if result:
            key, requestor_name, prom_data = result
            prom_info = json.dumps(prom_data)
            date, requestor = key
            
            # Generate embedding
            embedding = embed(prom_info, client)
            
            # Remove DB_PATH parameter - functions now use get_db_connection() directly
            msg_ids = get_ids_from_keys(key, requestor_name)
            if msg_ids:
                for list_of_msg_ids in msg_ids:
                    for msg_id in list_of_msg_ids:
                        doc_id = hashlib.sha256(msg_id.encode("utf-8")).hexdigest()
                        result = get_email_by_msgid(msg_id)
                        if result is None:
                            print(f"Warning: Could not find email for msg_id {msg_id}")
                            continue
                        email, file_name, start, end = result
                        insert_prom_record(
                            doc_id=doc_id,
                            date=date,
                            requestor=requestor,
                            requestor_name=requestor_name,
                            email_filename=file_name,
                            msg_start=start,
                            msg_end=end,
                            prom_info=prom_info,
                            embedding=embedding
                        )

    print(BANNER)
    print("Done inserting PROM records")
    print("Searching for PROM records...")

    hits = search_prom("The solution doesn't have an MSDS as it will be a mixture post-synthesis")
    for h in hits:
        print(h["distance"])
        print(h['date'])
        print(h['requestor'])
        print(h['prom_info'])