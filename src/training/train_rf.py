import os

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


# =========================================================
# 1. 전처리가 끝난 정상 데이터 불러오기
# =========================================================

df = pd.read_csv("data/normal_dataset.csv")

print("정상 데이터:", len(df), "건")


# =========================================================
# 2. AI에게 보여줄 입력값(Feature)
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


# AI가 맞혀야 하는 정답
TARGET = "target_temp_5m"


# =========================================================
# 3. 시간 순서대로 80% 학습 / 20% 테스트
# =========================================================

split_index = int(len(df) * 0.8)

train_df = df.iloc[:split_index]
test_df = df.iloc[split_index:]


# X = AI에게 주는 문제
X_train = train_df[FEATURES]

# y = 그 문제의 실제 정답
y_train = train_df[TARGET]


# 테스트용 문제
X_test = test_df[FEATURES]

# 테스트용 실제 정답
y_test = test_df[TARGET]


print()
print("학습 데이터:", len(X_train), "건")
print("테스트 데이터:", len(X_test), "건")


# =========================================================
# 4. RandomForest 모델 생성
# =========================================================

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1,
)


# =========================================================
# 5. AI 학습
# =========================================================

print()
print("모델 학습 시작...")

model.fit(
    X_train,
    y_train
)

print("모델 학습 완료")


# =========================================================
# 6. 테스트 데이터 예측
# =========================================================

predictions = model.predict(
    X_test
)


# =========================================================
# 7. 성능 평가
# =========================================================

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = (
    mean_squared_error(
        y_test,
        predictions
    )
    ** 0.5
)


print()
print("===== 정상 데이터 예측 성능 =====")

print(
    "MAE :",
    round(mae, 4),
    "℃"
)

print(
    "RMSE:",
    round(rmse, 4),
    "℃"
)


# =========================================================
# 8. 실제값 / 예측값 비교
# =========================================================

result = pd.DataFrame({
    "time": test_df["stat_date"].values,
    "actual": y_test.values,
    "predicted": predictions,
})

result["error"] = (
    result["actual"]
    - result["predicted"]
).abs()

print()
print("===== 예측 결과 일부 =====")

print(
    result
    .head(10)
    .to_string(index=False)
)


# =========================================================
# 9. 정상 상태의 예측 오차 분포 확인
# =========================================================

p95 = result["error"].quantile(0.95)
p99 = result["error"].quantile(0.99)
max_error = result["error"].max()

print()
print("===== 정상 상태 오차 분포 =====")
print("95% 오차 기준:", round(p95, 4), "℃")
print("99% 오차 기준:", round(p99, 4), "℃")
print("정상 최대 오차:", round(max_error, 4), "℃")


# =========================================================
# 10. 학습 완료된 모델 + 이상 판단 기준 저장
# =========================================================

os.makedirs(
    "models",
    exist_ok=True
)

MODEL_PATH = "models/temperature_rf.joblib"

model_package = {
    "model": model,
    "features": FEATURES,
    "threshold_95": p95,
    "threshold_99": p99,
}

joblib.dump(
    model_package,
    MODEL_PATH
)

print()
print("모델 저장 완료:")
print(MODEL_PATH)