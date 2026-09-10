# Taerin AI - 데이터센터 온도 예측 / 이상 감지 PoC

데이터센터의 센서 데이터를 이용하여 **정상적인 온도 변화를 학습하고, 예상 온도와 실제 온도의 차이를 이용해 이상 상황을 감지하는 AI PoC 프로젝트**입니다.

현재는 실제 고객 데이터 대신 가상 데이터를 생성하여 전체 AI 파이프라인을 테스트하고 있습니다.

---

## 1. 목표

전체적으로 만들고자 하는 흐름은 다음과 같습니다.

```text
센서 데이터
+
외부 날씨
+
시간 / 날짜 정보
        ↓
정상 온도 예측 모델
        ↓
5분 뒤 정상 예상 온도
        ↓
실제 센서 온도와 비교
        ↓
예측 오차 계산
        ↓
이상 여부 판단
        ↓
운영 이력 조회
        ↓
원인 후보 탐색
        ↓
LLM을 이용한 설명
```

예를 들어 모델이

```text
5분 뒤 예상 온도 : 27.5℃
실제 온도        : 29.0℃
```

라고 판단했다면 예측 오차를 이용하여 이상 상황인지 확인합니다.

이상이 감지되면 해당 시간대의 작업, 문 개방, 냉방 상태 등의 운영 이력을 조회하여 원인 후보를 찾는 것을 목표로 합니다.

---

# 2. Pipeline이란?

Pipeline(파이프라인)은

**데이터가 들어와 최종 결과가 나오기까지 거치는 전체 작업 순서**를 의미합니다.

현재 프로젝트의 파이프라인은 다음과 같습니다.

```text
data/generate_data.py
        ↓
PostgreSQL
        ↓
data/prepare_dataset.py
        ↓
normal_dataset.csv
event_dataset.csv
        ↓
training/train_rf.py
        ↓
temperature_rf.joblib
        ↓
evaluation/test_anomaly.py
        ↓
이상 감지
```

---

# 3. 프로젝트 구조

```text
taerin-ai/
│
├── data/
│   ├── normal_dataset.csv
│   └── event_dataset.csv
│
├── models/
│   └── temperature_rf.joblib
│
├── sql/
│
├── src/
│   ├── db.py
│   │
│   ├── data/
│   │   ├── generate_data.py
│   │   └── prepare_dataset.py
│   │
│   ├── training/
│   │   └── train_rf.py
│   │
│   ├── prediction/
│   │
│   └── evaluation/
│       └── test_anomaly.py
│
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

---

# 4. 파일별 역할

## `db.py`

PostgreSQL 연결을 담당합니다.

다른 Python 파일에서 DB 연결 정보(host, port, password 등)를 반복해서 작성하지 않고 다음과 같이 사용합니다.

```python
from db import get_connection

conn = get_connection()
```

즉,

```text
db.py
 ↓
PostgreSQL 연결
```

을 담당하는 공통 모듈입니다.

---

## `data/generate_data.py`

### 역할

실제 고객 데이터가 아직 없기 때문에 **가상의 데이터센터 데이터를 생성하는 PoC용 파일**입니다.

현재 약 30일의 데이터를 5분 간격으로 생성합니다.

```text
30일 × 24시간 × 시간당 12개
= 8,640개
```

생성하는 데이터는 크게 세 종류입니다.

```text
실내 센서 온도
외부 날씨
운영 이벤트
```

DB에는 다음과 같이 저장합니다.

```text
st_aisensor_5minute
→ 실내 센서 온도

ai_weather_history
→ 외기 온도 / 외부 습도

ai_operation_history
→ 문 개방 / 작업 / 냉방 정지 등의 운영 이력
```

현재 PoC에서는 일부러 다음과 같은 이벤트도 발생시킵니다.

```text
DOOR_OPEN
WORK
COOLING_OFF
```

예:

```text
13:55  27.50℃  NORMAL
14:00  27.88℃  DOOR_OPEN
14:05  28.20℃  DOOR_OPEN
...
14:40  29.41℃  DOOR_OPEN
```

실제 서비스에서는 실제 센서 데이터가 존재하므로 `generate_data.py`는 필요하지 않습니다.

---

## `data/prepare_dataset.py`

### 역할

DB의 원본 데이터를 **AI가 학습할 수 있는 문제(X)와 정답(y) 형태로 가공**합니다.

DB에는 기본적으로 시간별 센서값이 저장되어 있습니다.

```text
13:50 → 27.54℃
13:55 → 27.50℃
14:00 → 27.88℃
```

AI에게는 이를 다음과 같은 형태로 제공합니다.

```text
[입력 X]

현재 온도       27.50
5분 전          27.54
10분 전         ...
15분 전         ...
30분 전         ...
60분 전         ...

최근 5분 변화량
최근 30분 변화량

외기 온도
외부 습도

요일
시간 정보
날짜 정보


[정답 y]

5분 뒤 실제 온도
```

현재 사용하는 Feature:

```text
indoor_temp

temp_5m_ago
temp_10m_ago
temp_15m_ago
temp_30m_ago
temp_60m_ago

change_5m
change_30m

outdoor_temp
outdoor_humidity

weekday

time_sin
time_cos

date_sin
date_cos
```

`time_sin / time_cos`는 하루의 시간 주기를 표현합니다.

`date_sin / date_cos`는 1년의 날짜/계절 주기를 표현합니다.

### 정상 / 이벤트 데이터 분리

현재 PoC에서는 운영 이벤트가 발생한 시간 전후 데이터를 정상 학습에서 제외합니다.

결과:

```text
전체 학습 후보       : 8,627건
정상 학습 데이터     : 8,520건
이벤트 영향 데이터   : 107건
```

그리고 다음 파일로 저장합니다.

```text
data/normal_dataset.csv
data/event_dataset.csv
```

---

## `training/train_rf.py`

### 역할

`normal_dataset.csv`를 이용하여 **정상적인 온도 변화를 AI에게 학습시키는 파일**입니다.

현재 모델:

```text
RandomForestRegressor
```

정상 데이터 8,520건을 시간순으로 나눕니다.

```text
8,520건
   ↓

6,816건 (80%)
→ 학습 데이터

1,704건 (20%)
→ 테스트 데이터
```

랜덤으로 섞지 않고 시간순으로 나누는 이유는 실제 서비스에서도

```text
과거 데이터
 ↓
학습
 ↓
미래 데이터 예측
```

을 하기 때문입니다.

### X와 y

`X`는 AI에게 주는 정보입니다.

```text
현재 온도
과거 온도
온도 변화량
날씨
시간
날짜
...
```

`y`는 AI가 맞혀야 하는 정답입니다.

```text
5분 뒤 실제 온도
```

실제 학습은 다음 코드에서 수행됩니다.

```python
model.fit(X_train, y_train)
```

학습이 끝난 모델은 다음 위치에 저장됩니다.

```text
models/temperature_rf.joblib
```

이 파일은 **학습이 완료된 RandomForest 모델**입니다.

### 현재 PoC 결과

```text
MAE  : 0.0264℃
RMSE : 0.0310℃
```

단, 이 결과는 규칙을 직접 설정하여 생성한 **가상 데이터에 대한 결과**이므로 실제 데이터센터에서 동일한 정확도가 나온다는 의미는 아닙니다.

현재 단계에서는 전체 학습 파이프라인이 정상적으로 동작하는지 확인하기 위한 결과입니다.

---

## `evaluation/test_anomaly.py`

### 역할

정상 데이터만 학습한 모델에 이벤트 영향을 받은 데이터를 넣어 **이상 상황을 감지할 수 있는지 테스트**합니다.

기본 개념:

```text
정상 데이터를 학습한 AI
        ↓
5분 뒤 정상 온도 예측
        ↓
실제 5분 뒤 센서값 확인
        ↓
예측값과 실제값 차이 계산
        ↓
오차가 평소보다 큰가?
        ↓
YES
        ↓
이상 가능성
```

예:

```text
AI 예상 : 27.5℃
실제    : 29.0℃

오차    : 1.5℃
```

현재는 PoC를 위해 임시 임계값을 사용할 수 있지만, 최종적으로는 정상 데이터의 예측 오차 분포 등을 분석하여 이상 판단 기준을 결정해야 합니다.

---

# 5. 현재까지 진행 상황

```text
PostgreSQL DB 준비                  ✅

가상 센서 데이터 생성              ✅
외부 날씨 데이터 생성              ✅
운영 이벤트 생성                   ✅

AI Feature 생성                    ✅
정상 / 이벤트 데이터 분리          ✅

RandomForest 정상온도 학습          ✅
모델 저장                          ✅

이벤트 이상 감지 테스트             진행 중

운영이력 기반 원인 분석             예정
LLM 설명 생성                       예정

PyTorch / GRU 모델                  예정
RandomForest ↔ GRU 성능 비교        예정
```

---

# 6. 현재 AI 구조에서 중요한 개념

## Model

데이터를 학습하고 예측하는 AI 모델입니다.

현재:

```text
RandomForest
```

추후:

```text
GRU
```

도 테스트할 예정입니다.

---

## Framework

딥러닝 모델을 만들고 학습시키기 위한 도구입니다.

추후 사용할 예정:

```text
PyTorch
```

즉,

```text
PyTorch = 딥러닝 개발/학습 도구

GRU = PyTorch로 만들 수 있는
      시계열 딥러닝 모델 구조
```

입니다.

---

## Pipeline

AI 모델 하나만 의미하는 것이 아니라,

```text
데이터 수집
 ↓
전처리
 ↓
학습
 ↓
예측
 ↓
이상 감지
 ↓
원인 분석
 ↓
LLM 설명
```

까지 이어지는 **전체 작업 흐름**을 의미합니다.

---

# 7. 최종 목표

PoC가 완료되면 최종적으로 다음과 같은 흐름을 만드는 것이 목표입니다.

```text
데이터센터 센서
        +
외부 날씨 API
        ↓
정상 온도 예측
        ↓
실제값과 비교
        ↓
이상 감지
        ↓
관련 운영 이력 조회
        ↓
원인 후보 추출
        ↓
LLM
        ↓
사용자에게 설명
```

예시:

```text
예측 온도 : 27.4℃
실제 온도 : 29.1℃

정상 예측 범위에서 크게 벗어났습니다.

동시간대 출입문 개방 이력이 확인되어
온도 상승의 원인 후보로 판단됩니다.
```

※ LLM은 온도를 직접 예측하는 역할이 아니라, 예측 모델과 시스템이 찾아낸 결과를 바탕으로 사용자가 이해하기 쉬운 설명을 생성하는 역할로 사용합니다.


                 PostgreSQL
                     │
                     │ DB 연결
                     ▼
                  db.py
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
data/generate_data.py     data/prepare_dataset.py
        │                         │
        │ 테스트 데이터           │ Feature 생성
        │ DB 저장                 │ 정상/이벤트 분리
        ▼                         ▼
    PostgreSQL              data/
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
       normal_dataset.csv     event_dataset.csv
                  │                     │
                  ▼                     │
        training/train_rf.py           │
                  │                     │
                  ▼                     │
      temperature_rf.joblib             │
                  │                     │
                  └──────────┬──────────┘
                             ▼
                evaluation/test_anomaly.py
                             │
                             ▼
                   예측값 ↔ 실제값 비교
                             │
                             ▼
                         이상 감지