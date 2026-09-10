import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_connection


# =========================================================
# 1. DB 연결
# =========================================================

conn = get_connection()


# =========================================================
# 2. 센서 + 날씨 데이터 가져오기
# =========================================================

query = """
SELECT
    s.stat_date,
    s.avr_value AS indoor_temp,
    w.outdoor_temp,
    w.outdoor_humidity
FROM cms_schema.st_aisensor_5minute s
LEFT JOIN cms_schema.ai_weather_history w
    ON s.stat_date = w.measured_at
WHERE s.sensor_id = 1
ORDER BY s.stat_date
"""

df = pd.read_sql(query, conn)

operation_query = """
SELECT
    start_time,
    end_time,
    operation_type,
    description
FROM cms_schema.ai_operation_history
ORDER BY start_time
"""

operations_df = pd.read_sql(operation_query, conn)

conn.close()

print("DB에서 가져온 데이터:", len(df), "건")


# =========================================================
# 3. 날짜 타입 확인
# =========================================================

df["stat_date"] = pd.to_datetime(df["stat_date"])


# =========================================================
# 4. 과거 온도 Feature 만들기
# =========================================================

df["temp_5m_ago"] = df["indoor_temp"].shift(1)
df["temp_10m_ago"] = df["indoor_temp"].shift(2)
df["temp_15m_ago"] = df["indoor_temp"].shift(3)
df["temp_30m_ago"] = df["indoor_temp"].shift(6)
df["temp_60m_ago"] = df["indoor_temp"].shift(12)


# =========================================================
# 5. 최근 온도 변화량
# =========================================================

df["change_5m"] = (
    df["indoor_temp"]
    - df["temp_5m_ago"]
)

df["change_30m"] = (
    df["indoor_temp"]
    - df["temp_30m_ago"]
)


# =========================================================
# 6. 날짜 / 시간 Feature
# =========================================================

df["hour"] = df["stat_date"].dt.hour
df["minute"] = df["stat_date"].dt.minute
df["weekday"] = df["stat_date"].dt.weekday
df["day_of_year"] = df["stat_date"].dt.dayofyear


# =========================================================
# 7. 시간의 주기성 표현
# =========================================================

minute_of_day = (
    df["hour"] * 60
    + df["minute"]
)

df["time_sin"] = np.sin(
    2 * np.pi * minute_of_day / 1440
)

df["time_cos"] = np.cos(
    2 * np.pi * minute_of_day / 1440
)


# =========================================================
# 8. 날짜의 주기성 표현
# =========================================================

df["date_sin"] = np.sin(
    2 * np.pi * df["day_of_year"] / 365.25
)

df["date_cos"] = np.cos(
    2 * np.pi * df["day_of_year"] / 365.25
)


# =========================================================
# 9. AI가 맞혀야 할 정답
#    현재 시점 기준 5분 뒤 온도
# =========================================================

df["target_temp_5m"] = (
    df["indoor_temp"].shift(-1)
)


# =========================================================
# 10. 사용할 수 없는 행 제거
# =========================================================

df = df.dropna().copy()

# =========================================================
# 운영 이벤트의 영향을 받은 데이터 표시
# =========================================================

df["is_event_affected"] = False

BUFFER_MINUTES = 60

for _, operation in operations_df.iterrows():

    event_start = (
        pd.to_datetime(operation["start_time"])
        - pd.Timedelta(minutes=BUFFER_MINUTES)
    )

    event_end = (
        pd.to_datetime(operation["end_time"])
        + pd.Timedelta(minutes=BUFFER_MINUTES)
    )

    mask = (
        (df["stat_date"] >= event_start)
        & (df["stat_date"] <= event_end)
    )

    df.loc[mask, "is_event_affected"] = True


# =========================================================
# 11. AI에게 줄 Feature 목록
# =========================================================

FEATURES = [
    "indoor_temp",

    "temp_5m_ago",
    "temp_10m_ago",
    "temp_15m_ago",
    "temp_30m_ago",
    "temp_60m_ago",

    "change_5m",
    "change_30m",

    "outdoor_temp",
    "outdoor_humidity",

    "weekday",

    "time_sin",
    "time_cos",

    "date_sin",
    "date_cos",
]


# =========================================================
# 12. 결과 확인
# =========================================================

print()
print("학습 가능한 데이터:", len(df), "건")

print()
print("AI 입력 Feature:")
for feature in FEATURES:
    print(" -", feature)

print()
print("첫 번째 학습 문제:")
print(df[FEATURES + ["target_temp_5m"]].head(1).T)

normal_df = df[~df["is_event_affected"]].copy()
event_df = df[df["is_event_affected"]].copy()

print()
print("전체 학습 후보:", len(df))
print("정상 학습 데이터:", len(normal_df))
print("이벤트 영향 데이터:", len(event_df))

# =========================================================
# 학습/검증용 데이터 저장
# =========================================================

os.makedirs("data", exist_ok=True)

normal_df.to_csv(
    "data/normal_dataset.csv",
    index=False
)

event_df.to_csv(
    "data/event_dataset.csv",
    index=False
)

print()
print("데이터셋 저장 완료")
print(" - data/normal_dataset.csv")
print(" - data/event_dataset.csv")