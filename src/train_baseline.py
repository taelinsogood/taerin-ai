import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from db import get_connection

conn = get_connection()

query = """
SELECT
    stat_date,
    avr_value
FROM cms_schema.st_aisensor_5minute
WHERE sensor_id = 1
ORDER BY stat_date
"""

df = pd.read_sql(query, conn)

conn.close()

df["temp_5m_ago"] = df["avr_value"].shift(1)
df["temp_10m_ago"] = df["avr_value"].shift(2)
df["temp_15m_ago"] = df["avr_value"].shift(3)

df["hour"] = df["stat_date"].dt.hour
df["minute"] = df["stat_date"].dt.minute
df["weekday"] = df["stat_date"].dt.weekday

df["target_temp"] = df["avr_value"].shift(-1)

df = df.dropna()

features = [
    "avr_value",
    "temp_5m_ago",
    "temp_10m_ago",
    "temp_15m_ago",
    "hour",
    "minute",
    "weekday",
]

X = df[features]
y = df["target_temp"]

split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
)

# 진짜 학습 부분
model.fit(X_train, y_train)

# 처음 보는 데이터에 대해 다음 5분 온도 예측
pred = model.predict(X_test)

mae = mean_absolute_error(y_test, pred)

print("학습 완료")
print("테스트 데이터 개수:", len(X_test))
print("평균 절대 오차(MAE):", round(mae, 4), "℃")