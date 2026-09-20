import pandas as pd

from db import get_connection

# st_aisensor_5minute의 데이터를 가져오기

def load_sensor_data():
    conn = get_connection()

    query = """
        SELECT *
        FROM cms_schema.st_aisensor_5minute
        LIMIT 5;
    """

    df = pd.read_sql(query, conn)

    conn.close()

    return df


if __name__ == "__main__":
    df = load_sensor_data()

    print(df)
    print()
    print("컬럼 목록:")
    print(df.columns.tolist())