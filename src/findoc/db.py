import os
import psycopg
from pgvector.psycopg import register_vector

DSN = os.getenv("FINDOC_DSN", "postgresql://findoc:findoc@localhost:5433/findoc")


def connect():
    conn = psycopg.connect(DSN)
    register_vector(conn)     # bắt buộc: map numpy array <-> kiểu vector
    return conn
