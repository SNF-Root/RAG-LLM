"""
Test retrieval from email_embeddings table.
"""
import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from typing import List

load_dotenv()

# Stanford AI API Gateway
client = OpenAI(
    api_key=os.environ.get("STANFORD_API_KEY"),
    base_url="https://aiapi-prod.stanford.edu/v1"
)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "pgvector-db"),
        database=os.getenv("DB_NAME", "appdb"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "user"),
        password=os.getenv("DB_PASSWORD", "user_pw"),
    )


def embed_query(query: str) -> list[float]:
    """Embed a query string."""
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=query
    )
    return response.data[0].embedding


def search_emails(query: str, top_k: int = 5):
    """Search email embeddings by similarity."""
    query_embedding = embed_query(query)
    
    con = get_db_connection()
    cursor = con.cursor()
    
    cursor.execute("""
        SELECT 
            embedded_string,
            1 - (embedding <=> %s::vector) AS similarity
        FROM email_embeddings
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (query_embedding, query_embedding, top_k))
    
    results = cursor.fetchall()
    con.close()
    
    return results

def search_prom_req(query_embedding: List[float], con, top_k: int = 5):
    """Search email embeddings by similarity."""
    cursor = con.cursor()
    print("Searching for processes")
    cursor.execute("""
        SELECT 
            embedded_string,
            1 - (request_embedding <=> %s::vector) AS similarity
        FROM prom_embeddings
        ORDER BY request_embedding <=> %s::vector
        LIMIT %s
    """, (query_embedding, query_embedding, top_k))
    
    results = cursor.fetchall()
    
    return results


def search_prom_processes(query_embedding: List[float], con, top_k: int = 5):
    """Search email embeddings by similarity."""
    cursor = con.cursor()
    print("Searching for processes")
    cursor.execute("""
        SELECT embedded_string
            process_flow,
            1 - (process_embedding <=> %s::vector) AS similarity
        FROM prom_embeddings
        ORDER BY process_embedding <=> %s::vector
        LIMIT %s
    """, (query_embedding, query_embedding, top_k))
    
    results = cursor.fetchall()
    
    return results




def print_results(results):
    """Pretty print search results."""
    print("\n" + "=" * 80)
    print("SEARCH RESULTS")
    print("=" * 80)
    
    for i, row in enumerate(results, 1):
        raw_thread, similarity = row
        print(f"\n--- Result {i} (similarity: {similarity:.4f}) ---")
        print(f"\n{raw_thread}")
        print("-" * 80)


if __name__ == "__main__":
    # Example queries based on actual email content
    test_queries = [
        "Can I bring in a new developer for e-beam resist AR-N 7520?",
        "Is it okay to etch silicon in lampoly if the lithium niobate is covered by resist?",
        "What are the concerns with spin coating nanoparticle solutions in the cleanroom?",
    ]

    con = get_db_connection()
    counter = 0
    while counter != 6:
        print("Select a query to test:")
        for i, q in enumerate(test_queries, 1):
            print(f"  {i}. {q}")
        print(f"  {len(test_queries) + 1}. Enter custom query")
        
        choice = input(f"\nEnter choice (1-{len(test_queries) + 1}): ").strip()
        query = input("Enter your query: ").strip()
        select_mode = input("Press 1 for searching requests, press 2 for processes: ")
        print(f"\nSearching for: '{query}'")
        embedded_query = embed_query(query)
        if int(select_mode) == 1:
            results = search_prom_req(query_embedding=embedded_query, con=con, top_k=2)
        else:
            results = search_prom_processes(query_embedding=embedded_query, con=con, top_k=2)
            if results: 
                print_results(results)
            else:
                print("DOES NOT RETURN RESULTS")
            counter += 1
    
    con.close()
    print("SPENT ENOUGH MONEY")


