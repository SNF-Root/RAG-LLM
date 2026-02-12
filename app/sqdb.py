import psycopg2
import time
from orderEmails import create_dict_of_threads, get_email_by_msgid
from database.pg import get_db_connection, init_email_table
from filter_emails import extract_main_message
from embed_emails import run_pipeline
import asyncio
from models.insert import Email



BANNER = r"""
/******************************************************************************\
*                                                                              *
*                         N E X T   E M A I L   T H R E A D                    *
*                                                                              *
\******************************************************************************/
"""





# def init_db(con = None):
#     """Initialize database tables. Pass existing connection to reuse it."""
#     should_close = False
#     if con is None:
#         con = get_db_connection
#         should_close = True
#     con = get_db_connection()
#     cursor = con.cursor()

#     # Enable pgvector extension
#     cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

#     # Drop old table to recreate with correct schema
#     cursor.execute("DROP TABLE IF EXISTS email_embeddings")

#     cursor.execute("""
#     CREATE TABLE IF NOT EXISTS email_embeddings (
#         email_id SERIAL PRIMARY KEY,
#         date VARCHAR(20) NOT NULL,
#         requestor VARCHAR(100) NOT NULL,
#         filename VARCHAR(100) NOT NULL,
#         prom_approval VARCHAR(50),
#         prom_considerations TEXT NOT NULL,
#         chemicals TEXT NOT NULL,
#         processes TEXT NOT NULL,
#         raw_thread TEXT NOT NULL,
#         embedded_string TEXT NOT NULL,
#         embedding vector(1536) NOT NULL,
#         UNIQUE (date, filename, requestor, chemicals, processes)
#     )
#     """)

#     # NO HNSW here - build after bulk insert via create_hnsw_idx()

#     print("successfully initiated database")
#     con.commit()

#     if should_close:
#         con.close()
#         return None
    
#     return con  


# def create_hnsw_idx(con=None):
#     """Build HNSW index on prom_embeddings. Call AFTER bulk insert."""
#     should_close = False
#     if con is None:
#         con = get_db_connection()
#         should_close = True
    
#     cursor = con.cursor()
#     cursor.execute("""
#     CREATE INDEX IF NOT EXISTS prom_emb_idx 
#     ON prom_embeddings USING hnsw(embedding vector_cosine_ops)
#     """)
#     con.commit()
    
#     if should_close:
#         con.close()
#         return None
#     return con



# def populate_db(filename: str, msg_start: Dict[str, int], msg_end: Dict[str, int], dict_of_threads: Dict[Tuple[str, str], List[List[str]]], requestor_names: Dict[Tuple[str, str], str] = None):
#     con = get_db_connection()
#     cursor = con.cursor()

#     if requestor_names is None:
#         requestor_names = {}

#     rows = []
#     for (date, requestor), threads in dict_of_threads.items():
#         if (date, requestor) != ("", ""):
#             requestor_name = requestor_names.get((date, requestor), "")
#             # print(f"date: {date}, requestor: {requestor}, requestor_name: {requestor_name}")
#             rows.append((date, requestor, requestor_name, json.dumps(threads)))
    
#     cursor.executemany("""
#     INSERT INTO threads_by_key(date, requestor, requestor_name, msgid_json)
#     VALUES(%s, %s, %s, %s)
#     ON CONFLICT (date, requestor, msgid_json) DO NOTHING
#     """, rows)


#     for msg_id in msg_start:
#         msg_rows = [(msg_id, filename, msg_start[msg_id], msg_end[msg_id])]
    

#         cursor.executemany("""
#             INSERT INTO retrieve_msgs(msgid, file_name, start, "end")
#             VALUES(%s, %s, %s, %s)
#             ON CONFLICT (msgid) DO NOTHING
#         """, msg_rows)

#     con.commit()
#     con.close()


# def get_ids_from_keys(key: Tuple[str, str], requestor_full_name: str):
#     con = get_db_connection()
#     cursor = con.cursor()

#     date, requestor = key
    
#     # Only include requestor_name condition if it's not empty (prevents matching everything)
#     if requestor_full_name:
#         cursor.execute("""
#         SELECT msgid_json FROM threads_by_key
#         WHERE date = %s 
#         AND (
#             requestor LIKE '%%' || %s || '%%' 
#             OR requestor_name LIKE '%%' || %s || '%%'
#         )
#         """, (date, requestor, requestor_full_name))
#     else:
#         cursor.execute("""
#         SELECT msgid_json FROM threads_by_key 
#         WHERE date = %s 
#         AND requestor LIKE '%%' || %s || '%%'
#         """, (date, requestor))
    
#     rows = cursor.fetchall()
#     con.close() 

#     if len(rows) == 0:
#         return None
#     elif len(rows) == 1:
#         return json.loads(rows[0][0])
#     else:
#         return [json.loads(row) for row in rows]

# def get_email_by_msgid_from_db(msgid: str) -> str:
#     con = get_db_connection()
#     cursor = con.cursor()

#     cursor.execute("""
#     SELECT file_name, start, "end" FROM retrieve_msgs WHERE msgid = %s
#     """, (msgid,))
    
#     row = cursor.fetchone()
#     con.close()
    
#     if row is None:
#         return None
#     else:
#         file_name, start, end = row
#         with open(file_name, "r", errors="replace") as f:
#             if end is None:
#                 f.seek(0, 2)
#                 end = f.tell()
#             f.seek(start)
#             email = f.read(end - start)
#             return email

if __name__ == "__main__":

    path = "/app/emails/"
    files = ["emails.txt", "emails2.txt", "emails3.txt", "juneEmails.txt"]
    con = get_db_connection()
    init_email_table(con)
    for file in files:
        file_path = path+file
        dict_of_threads, msg_start, msg_end, requestor_names = create_dict_of_threads(file_path)
        
        if not dict_of_threads:
            print(f"No threads found in {file_path}")
            continue
        email_objects = []
        for keys, vals in dict_of_threads.items():
            date, requestor = keys
            for val in vals:
                thread = ""
                for item in val:
                    email = get_email_by_msgid(file_path, msg_start, msg_end, item)
                    processed_email = extract_main_message(email)
                    thread = thread + "\n" + processed_email
                email_object = Email(date=date, filepath=file_path, requestor=requestor, raw_thread=thread)
                email_objects.append(email_object)
        print(f"created {len(email_objects)} email objects")
        results = asyncio.run(run_pipeline(email_objects, con))
        print("finished populating db")


#DONT FORGET TO ADD RATE LIMITING