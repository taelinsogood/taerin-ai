import pandas as pd
import numpy as np


# st_aisensor_5minute의 데이터를 가져와서 AI가 학습하기 좋은 형태로 정리
# avr_value를 이용하여 5분 단위 표 생성

def make_features(df):
    df = df.copy()

    # 센서별 + 시간순으로 정렬
    df = df.sort_values(
        ["sensor_id", "stat_date"]
    ).reset_index(drop=True)

    # 현재 실내온도
    df["indoor_temp"] = df["avr_value"]

    # 같은 센서의 과거 온도만 가져오기
    df["temp_5m_ago"] = (
        df.groupby("sensor_id")["indoor_temp"].shift(1)
    )

    df["temp_10m_ago"] = (
        df.groupby("sensor_id")["indoor_temp"].shift(2)
    )

    df["temp_30m_ago"] = (
        df.groupby("sensor_id")["indoor_temp"].shift(6)
    )

    df["temp_60m_ago"] = (
        df.groupby("sensor_id")["indoor_temp"].shift(12)
    )

    # 온도 변화량
    df["change_5m"] = (
        df["indoor_temp"] - df["temp_5m_ago"]
    )

    df["change_30m"] = (
        df["indoor_temp"] - df["temp_30m_ago"]
    )

    df["change_60m"] = (
        df["indoor_temp"] - df["temp_60m_ago"]
    )

    # 시간 정보
    df["hour"] = (
        df["stat_date"].dt.hour
        + df["stat_date"].dt.minute / 60
    )

    df["weekday"] = df["stat_date"].dt.weekday
    df["month"] = df["stat_date"].dt.month

    # 하루 24시간의 반복성을 표현
    df["time_sin"] = np.sin(
        2 * np.pi * df["hour"] / 24
    )

    df["time_cos"] = np.cos(
        2 * np.pi * df["hour"] / 24
    )

    # 1년 중 몇 번째 날인지
    df["day_of_year"] = df["stat_date"].dt.dayofyear

    # 1년의 반복성을 표현
    df["date_sin"] = np.sin(
        2 * np.pi * df["day_of_year"] / 365.25
    )

    df["date_cos"] = np.cos(
        2 * np.pi * df["day_of_year"] / 365.25
    )

    return df


# ↓ 여기부터는 make_features 함수 밖
if __name__ == "__main__":

    # 동작 확인을 위한 임시 데이터
    test_df = pd.DataFrame({
        "sensor_id": [1, 1, 1, 1, 1, 1, 1],
        "stat_date": pd.date_range(
            start="2026-09-19 09:00",
            periods=7,
            freq="5min"
        ),
        "avr_value": [
            24.0,
            24.1,
            24.2,
            24.3,
            24.4,
            24.5,
            24.6
        ]
    })

    result = make_features(test_df)

    print(
        result[
            [
                "stat_date",
                "indoor_temp",
                "temp_5m_ago",
                "temp_10m_ago",
                "temp_30m_ago",
                "change_5m",
                "change_30m",
            ]
        ].to_string(index=False)
    )