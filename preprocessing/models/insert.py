from dataclasses import asdict, dataclass, replace
from typing import Optional, List
import psycopg2

@dataclass(frozen=True)
class Email:
    date: str
    filepath: str
    requestor: str
    prom_approval: Optional [str] = None
    prom_considerations: Optional [str] = None
    chemicals: Optional[str] = None
    processes: Optional[str] = None
    raw_thread: Optional[str] = None
    embedded_string: Optional[str] = None
    embedding: Optional[list[float]] = None


    def insert_email(self, con):
        cursor = con.cursor()
        cursor.execute("""
        INSERT INTO email_embeddings (date, filename, requestor, prom_approval, prom_considerations, chemicals, processes, raw_thread, embedded_string, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date, filename, requestor, chemicals, processes) DO NOTHING
        """, (self.date, self.filepath, self.requestor, self.prom_approval, self.prom_considerations, self.chemicals, self.processes, self.raw_thread, self.embedded_string, self.embedding))
        con.commit()
        return cursor.rowcount

@dataclass(frozen=True)
class PromForm:
    date: str
    filename: str
    requestor: str
    request_title: Optional[str] = None
    chemicals_and_processes: Optional[str] = None
    request_reason: Optional[str] = None
    process_flow: Optional[str] = None
    amount_and_form: Optional[str] = None
    staff_considerations: Optional[str] = None
    raw_prom: Optional[str] = None
    embedded_string: Optional[str] = None
    request_embedding: Optional[list[float]] = None
    process_embedding: Optional[list[float]] = None


    def insert_prom(self, con):
        cursor = con.cursor()
        cursor.execute("""
        INSERT INTO prom_embeddings (date, filename, requestor, request_title, chemicals_and_processes, request_reason, process_flow, amount_and_form, staff_considerations, raw_prom, embedded_string, request_embedding, process_embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date, requestor, request_title) DO NOTHING
        """, (self.date, self.filename, self.requestor, self.request_title, self.chemicals_and_processes, self.request_reason, self.process_flow, self.amount_and_form, self.staff_considerations, self.raw_prom, self.embedded_string, self.request_embedding, self.process_embedding))
        con.commit()
        return cursor.rowcount

    def is_empty(self) -> List[str]:
        return [field for field, value in asdict(self).items() if value is None]