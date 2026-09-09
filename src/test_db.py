import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

conn = psycopg.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT COUNT(*)
        FROM cms_schema.st_aisensor_5minute
    """)

    count = cur.fetchone()[0]

print("DB 연결 성공")
print("온도 데이터 개수:", count)

conn.close()