from db import get_connection

conn = get_connection()

with conn.cursor() as cur:
    cur.execute("""
        SELECT COUNT(*)
        FROM cms_schema.st_aisensor_5minute
    """)

    count = cur.fetchone()[0]

print("DB 연결 성공")
print("온도 데이터 개수:", count)

conn.close()