import joblib
import pandas as pd


# =========================================================
# 1. 학습된 모델 불러오기
# =========================================================

MODEL_PATH = "models/temperature_rf.joblib"

model_package = joblib.load(MODEL_PATH)

model = model_package["model"]
FEATURES = model_package["features"]
threshold_95 = model_package["threshold_95"]
threshold_99 = model_package["threshold_99"]

print("학습된 모델 불러오기 완료")
print("95% 이상 기준:", round(threshold_95, 4), "℃")
print("99% 이상 기준:", round(threshold_99, 4), "℃")

print("학습된 모델 불러오기 완료")


# =========================================================
# 2. 이벤트 데이터 불러오기
# =========================================================

df = pd.read_csv("data/event_dataset.csv")

print("이벤트 영향 데이터:", len(df), "건")


# =========================================================
# 3. 모델 학습 때 사용했던 Feature
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

TARGET = "target_temp_5m"


# =========================================================
# 4. 이벤트 상황에서 5분 뒤 정상온도 예측
# =========================================================

X = df[FEATURES]

predictions = model.predict(X)


# =========================================================
# 5. 실제값과 예측값 비교
# =========================================================

df["predicted_temp"] = predictions

df["prediction_error"] = (
    df[TARGET]
    - df["predicted_temp"]
).abs()


# =========================================================
# 6. 우선 임시 기준으로 이상 여부 판단
# =========================================================
#
# 아직 0.20℃가 최종 기준이라는 뜻이 아니다.
# 지금은 PoC에서 결과를 보기 위한 임시값.
#

ANOMALY_THRESHOLD = threshold_99

df["is_anomaly"] = (
    df["prediction_error"]
    >= ANOMALY_THRESHOLD
)


# =========================================================
# 7. 결과 출력
# =========================================================

result = df[
    [
        "stat_date",
        "indoor_temp",
        "target_temp_5m",
        "predicted_temp",
        "prediction_error",
        "is_anomaly",
    ]
]


print()
print("===== 이벤트 데이터 예측 결과 =====")

print(
    result.to_string(
        index=False
    )
)


# =========================================================
# 8. 요약
# =========================================================

anomaly_count = df["is_anomaly"].sum()

print()
print("===== 이상 감지 결과 =====")

print(
    "전체 이벤트 영향 데이터:",
    len(df),
    "건"
)

print(
    "이상으로 감지:",
    anomaly_count,
    "건"
)

print(
    "최대 예측 오차:",
    round(
        df["prediction_error"].max(),
        4
    ),
    "℃"
)

print(
    "평균 예측 오차:",
    round(
        df["prediction_error"].mean(),
        4
    ),
    "℃"
)

from db import get_connection

# =========================================================
# 9. 실제 운영 이벤트 조회
# =========================================================

conn = get_connection()

operation_query = """
SELECT
    start_time,
    end_time,
    operation_type,
    description
FROM cms_schema.ai_operation_history
ORDER BY start_time
"""

operations_df = pd.read_sql(
    operation_query,
    conn
)

conn.close()

operations_df["start_time"] = pd.to_datetime(
    operations_df["start_time"]
)

operations_df["end_time"] = pd.to_datetime(
    operations_df["end_time"]
)

df["stat_date"] = pd.to_datetime(
    df["stat_date"]
)


# =========================================================
# 10. 이벤트별 최초 이상 감지 시점 확인
# =========================================================

print()
print("===== 이벤트별 이상 감지 =====")

for _, operation in operations_df.iterrows():

    start_time = operation["start_time"]
    end_time = operation["end_time"]

    event_rows = df[
        (df["stat_date"] >= start_time)
        &
        (df["stat_date"] <= end_time)
    ].copy()

    anomaly_rows = event_rows[
        event_rows["is_anomaly"]
    ]

    print()
    print(
        "이벤트:",
        operation["operation_type"]
    )

    print(
        "기간:",
        start_time,
        "~",
        end_time
    )

    print(
        "설명:",
        operation["description"]
    )

    print(
        "이벤트 구간 데이터:",
        len(event_rows),
        "건"
    )

    print(
        "이상 감지:",
        len(anomaly_rows),
        "건"
    )

    if len(anomaly_rows) > 0:

        first_detected = (
            anomaly_rows
            .iloc[0]["stat_date"]
        )

        delay_minutes = (
            first_detected
            - start_time
        ).total_seconds() / 60

        print(
            "최초 이상 감지:",
            first_detected
        )

        print(
            "감지 지연:",
            int(delay_minutes),
            "분"
        )

        print(
            "최초 감지 오차:",
            round(
                anomaly_rows
                .iloc[0]["prediction_error"],
                4
            ),
            "℃"
        )

    else:

        print(
            "이 이벤트는 이상으로 감지되지 않음"
        )