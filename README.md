taerin-ai/
│
├─ data/
│  ├─ normal_horizon_dataset.csv
│  └─ event_horizon_dataset.csv
│
├─ models/
│  └─ temperature_rf_horizon_8h.joblib
│
├─ src/
│  │
│  ├─ db.py
│  │    └─ DB 연결
│  │
│  ├─ load_data.py
│  │    └─ DB에서 원본 데이터 조회
│  │       - 실내 센서
│  │       - 외기온도/습도
│  │       - 기상예보
│  │       - 운영이력
│  │
│  ├─ make_features.py       ⭐ X 담당
│  │    └─ 모델 입력값 생성
│  │       - 현재 실내온도
│  │       - 과거온도 Lag
│  │       - 온도 변화량
│  │       - 현재 외기/습도
│  │       - 시간/요일/계절
│  │       - horizon
│  │       - 미래 시각
│  │       - 미래 기상예보
│  │
│  ├─ make_targets.py        ⭐ y 담당
│  │    └─ 학습용 정답 생성
│  │       - 5분 뒤 실제온도
│  │       - 10분 뒤 실제온도
│  │       - ...
│  │       - 480분 뒤 실제온도
│  │
│  ├─ prepare_dataset.py
│  │    └─ 학습 Dataset 조립
│  │
│  │       load_data
│  │           ↓
│  │       make_features → X
│  │           +
│  │       make_targets  → y
│  │           ↓
│  │       이벤트 구간 처리
│  │           ↓
│  │       정상 / 이벤트 분리
│  │           ↓
│  │       CSV 저장
│  │
│  ├─ train_model.py
│  │    └─ 모델 학습/검증
│  │       - Train/Test 시간순 분리
│  │       - model.fit(X, y)
│  │       - model.predict(X_test)
│  │       - MAE / RMSE
│  │       - +1h/+2h/+4h/+6h/+8h 평가
│  │       - 모델 저장
│  │
│  ├─ predict.py
│  │    └─ 실제 운영 예측
│  │       - 최신 데이터 조회
│  │       - make_features 재사용 ⭐
│  │       - 96개 horizon 생성
│  │       - model.predict()
│  │       - 예측 DB 저장
│  │
│  └─ evaluate_predictions.py
│       └─ 실제값 도착 후
│          - 과거 예측값 조회
│          - 실제값 비교
│          - residual 계산
│          - 이상 여부 판단
│
└─ README.md


--------------------------

[학습할 때]

DB
 ↓
load_data
 ↓
make_features ──→ X
make_targets  ──→ y
 ↓
prepare_dataset
 ↓
train_model


[실제로 예측할 때]

현재 DB
 ↓
load_data
 ↓
make_features ──→ X
 ↓
predict
 ↓
향후 8시간 온도

--------------------------------

① load_data.py
   DB에서 원본 데이터 가져오기
        ↓
② make_features.py
   X 만들기
        ↓
③ make_targets.py
   y 만들기
        ↓
④ prepare_dataset.py
   X + y 합쳐서 학습 데이터 완성
        ↓
⑤ train_model.py
   모델 학습 + 테스트
        ↓
⑥ predict.py
   실제 8시간 예측
        ↓
⑦ evaluate_predictions.py
   실제값 도착 후 예측값과 비교 + 이상감지