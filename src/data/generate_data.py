import math
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_connection


# =========================================================
# 1. DB 연결
# =========================================================

conn = get_connection()


# =========================================================
# 2. 테스트 데이터센터 설정
# =========================================================

START_TIME = datetime(2026, 8, 1, 0, 0)

DAYS = 30

SENSOR_ID = 1
INTERFACE_ID = 1


# =========================================================
# 3. 일부러 발생시킬 운영 이벤트
# =========================================================

operations = [
    {
        "start": datetime(2026, 8, 5, 14, 0),
        "end": datetime(2026, 8, 5, 14, 40),
        "type": "DOOR_OPEN",
        "description": "출입문 장시간 개방",
    },
    {
        "start": datetime(2026, 8, 12, 2, 0),
        "end": datetime(2026, 8, 12, 3, 0),
        "type": "WORK",
        "description": "새벽 장비 작업",
    },
    {
        "start": datetime(2026, 8, 20, 16, 0),
        "end": datetime(2026, 8, 20, 17, 0),
        "type": "COOLING_OFF",
        "description": "냉방 장비 정지",
    },
]


# =========================================================
# 4. 생성한 데이터를 임시로 담을 공간
# =========================================================

weather_rows = []
sensor_rows = []

previous_indoor_temp = 27.0

# 5분마다 1개
# 1시간 = 12개
# 1일 = 288개
# 30일 = 8640개
total_steps = DAYS * 24 * 12


# =========================================================
# 5. 5분마다 데이터 생성
# =========================================================

for i in range(total_steps):

    current_time = START_TIME + timedelta(minutes=i * 5)

    hour = current_time.hour + current_time.minute / 60


    # -----------------------------------------------------
    # A. 외부 날씨 생성
    # -----------------------------------------------------

    outdoor_temp = (
        28
        + 5 * math.sin((hour - 8) / 24 * 2 * math.pi)
        + random.uniform(-0.3, 0.3)
    )

    outdoor_humidity = (
        65
        - 10 * math.sin((hour - 8) / 24 * 2 * math.pi)
        + random.uniform(-2, 2)
    )


    # -----------------------------------------------------
    # B. 정상적인 실내 온도
    # -----------------------------------------------------

    target_indoor_temp = (
        27.0
        + (outdoor_temp - 28.0) * 0.12
    )

    indoor_temp = (
        previous_indoor_temp * 0.85
        + target_indoor_temp * 0.15
        + random.uniform(-0.05, 0.05)
    )


    # -----------------------------------------------------
    # C. 특별한 운영 이벤트가 있으면 온도에 영향
    # -----------------------------------------------------

    for operation in operations:

        if operation["start"] <= current_time <= operation["end"]:

            if operation["type"] == "DOOR_OPEN":
                indoor_temp += 0.35

            elif operation["type"] == "WORK":
                indoor_temp += 0.25

            elif operation["type"] == "COOLING_OFF":
                indoor_temp += 0.50


    previous_indoor_temp = indoor_temp


    # -----------------------------------------------------
    # D. 날씨 데이터 저장 준비
    # -----------------------------------------------------

    weather_rows.append(
        (
            current_time,
            outdoor_temp,
            outdoor_humidity,
        )
    )


    # -----------------------------------------------------
    # E. 센서 데이터 저장 준비
    # -----------------------------------------------------

    sensor_rows.append(
        (
            "AI",
            "TEST",
            "TEMP",

            INTERFACE_ID,
            SENSOR_ID,

            indoor_temp - 0.1,
            indoor_temp,
            indoor_temp + 0.1,

            5,

            current_time,
            current_time + timedelta(minutes=5),
            current_time,

            current_time.strftime("%a"),
        )
    )


# =========================================================
# 6. DB에 실제 INSERT
# =========================================================

with conn.cursor() as cur:

    # 날씨
    cur.executemany(
        """
        INSERT INTO cms_schema.ai_weather_history (
            measured_at,
            outdoor_temp,
            outdoor_humidity
        )
        VALUES (%s, %s, %s)
        """,
        weather_rows,
    )


    # 센서
    cur.executemany(
        """
        INSERT INTO cms_schema.st_aisensor_5minute (
            system_type,
            system_group,
            system_name,
            intf_id,
            sensor_id,
            min_value,
            avr_value,
            max_value,
            stat_cnt,
            start_date,
            end_date,
            stat_date,
            stat_week
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """,
        sensor_rows,
    )


    # 운영이력
    for operation in operations:

        cur.execute(
            """
            INSERT INTO cms_schema.ai_operation_history (
                start_time,
                end_time,
                operation_type,
                location_id,
                description
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                operation["start"],
                operation["end"],
                operation["type"],
                1,
                operation["description"],
            ),
        )


conn.commit()
conn.close()


print("가상 데이터센터 데이터 생성 완료")
print("센서 데이터:", len(sensor_rows))
print("날씨 데이터:", len(weather_rows))
print("운영 이벤트:", len(operations))