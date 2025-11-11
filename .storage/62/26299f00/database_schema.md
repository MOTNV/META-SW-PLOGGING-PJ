# 플로깅 앱 데이터베이스 스키마 설계

## 개요
플로깅(Plogging) 앱의 모든 기능을 지원하기 위한 데이터베이스 구조입니다.

## 테이블 구조

### 1. users (사용자 정보)
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(50) UNIQUE NOT NULL,
  full_name VARCHAR(100),
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- 사용자 통계
  total_distance DECIMAL(10,2) DEFAULT 0, -- 총 거리 (km)
  total_duration INTEGER DEFAULT 0, -- 총 운동 시간 (초)
  total_calories INTEGER DEFAULT 0, -- 총 칼로리
  total_trash_collected INTEGER DEFAULT 0, -- 총 쓰레기 수집 개수
  level INTEGER DEFAULT 1, -- 사용자 레벨
  experience_points INTEGER DEFAULT 0 -- 경험치
);
```

### 2. plogging_sessions (플로깅 세션)
```sql
CREATE TABLE plogging_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- 운동 정보
  start_time TIMESTAMP WITH TIME ZONE NOT NULL,
  end_time TIMESTAMP WITH TIME ZONE,
  duration INTEGER, -- 운동 시간 (초)
  distance DECIMAL(10,2), -- 거리 (km)
  average_speed DECIMAL(5,2), -- 평균 속도 (km/h)
  max_speed DECIMAL(5,2), -- 최고 속도 (km/h)
  calories_burned INTEGER, -- 소모 칼로리
  
  -- 플로깅 특화 정보
  trash_collected INTEGER DEFAULT 0, -- 수집한 쓰레기 개수
  route_data JSONB, -- GPS 경로 데이터
  
  -- 위치 정보
  start_latitude DECIMAL(10,8),
  start_longitude DECIMAL(11,8),
  end_latitude DECIMAL(10,8),
  end_longitude DECIMAL(11,8),
  
  -- 메타데이터
  weather_condition VARCHAR(50), -- 날씨 상태
  notes TEXT, -- 사용자 메모
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3. route_points (GPS 경로 포인트)
```sql
CREATE TABLE route_points (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES plogging_sessions(id) ON DELETE CASCADE,
  latitude DECIMAL(10,8) NOT NULL,
  longitude DECIMAL(11,8) NOT NULL,
  altitude DECIMAL(8,2), -- 고도 (m)
  accuracy DECIMAL(6,2), -- GPS 정확도 (m)
  speed DECIMAL(5,2), -- 순간 속도 (km/h)
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  point_order INTEGER NOT NULL -- 경로상 순서
);
```

### 4. trash_collections (쓰레기 수집 기록)
```sql
CREATE TABLE trash_collections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES plogging_sessions(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- 쓰레기 정보
  trash_type VARCHAR(50) NOT NULL, -- 플라스틱, 캔, 종이, 기타
  quantity INTEGER DEFAULT 1, -- 수량
  
  -- 위치 정보
  latitude DECIMAL(10,8),
  longitude DECIMAL(11,8),
  location_name VARCHAR(200), -- 장소명
  
  -- 사진
  photo_url TEXT, -- 쓰레기 사진
  
  -- 메타데이터
  collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  notes TEXT -- 메모
);
```

### 5. achievements (업적/뱃지)
```sql
CREATE TABLE achievements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  description TEXT,
  icon_url TEXT,
  category VARCHAR(50), -- distance, trash, time, streak 등
  requirement_value INTEGER, -- 달성 조건 값
  experience_reward INTEGER DEFAULT 0, -- 경험치 보상
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 6. user_achievements (사용자 업적)
```sql
CREATE TABLE user_achievements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  achievement_id UUID REFERENCES achievements(id) ON DELETE CASCADE,
  achieved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, achievement_id)
);
```

### 7. user_stats_daily (일별 통계)
```sql
CREATE TABLE user_stats_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  
  -- 일별 통계
  sessions_count INTEGER DEFAULT 0,
  total_distance DECIMAL(10,2) DEFAULT 0,
  total_duration INTEGER DEFAULT 0,
  total_calories INTEGER DEFAULT 0,
  trash_collected INTEGER DEFAULT 0,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, date)
);
```

### 8. challenges (챌린지)
```sql
CREATE TABLE challenges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(200) NOT NULL,
  description TEXT,
  challenge_type VARCHAR(50), -- daily, weekly, monthly
  target_value INTEGER, -- 목표값
  target_metric VARCHAR(50), -- distance, trash, sessions
  start_date DATE,
  end_date DATE,
  reward_experience INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 9. user_challenges (사용자 챌린지 참여)
```sql
CREATE TABLE user_challenges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  challenge_id UUID REFERENCES challenges(id) ON DELETE CASCADE,
  current_progress INTEGER DEFAULT 0,
  is_completed BOOLEAN DEFAULT false,
  completed_at TIMESTAMP WITH TIME ZONE,
  joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, challenge_id)
);
```

## 데이터베이스 관계도

```
auth.users (Supabase Auth)
    ↓ (1:N)
plogging_sessions ←→ route_points (1:N)
    ↓ (1:N)
trash_collections

auth.users
    ↓ (1:N)
user_stats_daily

achievements ←→ user_achievements ←→ auth.users (N:M)

challenges ←→ user_challenges ←→ auth.users (N:M)
```

## 인덱스 설계

```sql
-- 성능 최적화를 위한 인덱스
CREATE INDEX idx_sessions_user_id ON plogging_sessions(user_id);
CREATE INDEX idx_sessions_start_time ON plogging_sessions(start_time);
CREATE INDEX idx_route_points_session_id ON route_points(session_id);
CREATE INDEX idx_route_points_timestamp ON route_points(timestamp);
CREATE INDEX idx_trash_collections_session_id ON trash_collections(session_id);
CREATE INDEX idx_trash_collections_user_id ON trash_collections(user_id);
CREATE INDEX idx_user_stats_user_date ON user_stats_daily(user_id, date);
```

## Row Level Security (RLS) 정책

```sql
-- 사용자는 자신의 데이터만 접근 가능
ALTER TABLE plogging_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own sessions" ON plogging_sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own sessions" ON plogging_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own sessions" ON plogging_sessions FOR UPDATE USING (auth.uid() = user_id);

ALTER TABLE route_points ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own route points" ON route_points 
  FOR SELECT USING (auth.uid() IN (SELECT user_id FROM plogging_sessions WHERE id = session_id));

ALTER TABLE trash_collections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own trash collections" ON trash_collections FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own trash collections" ON trash_collections FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 다른 테이블들도 동일한 패턴으로 RLS 적용
```

## 기능별 데이터 흐름

### 1. 플로깅 세션 시작
1. `plogging_sessions` 테이블에 새 세션 생성
2. GPS 포인트를 `route_points`에 실시간 저장
3. 쓰레기 수집 시 `trash_collections`에 기록

### 2. 세션 종료
1. `plogging_sessions` 업데이트 (종료 시간, 통계)
2. `user_stats_daily` 일별 통계 업데이트
3. 업적 달성 확인 및 `user_achievements` 업데이트

### 3. 히스토리 조회
1. `plogging_sessions`에서 사용자 세션 목록 조회
2. 필요 시 `route_points`와 `trash_collections` 조인

### 4. 통계 대시보드
1. `user_stats_daily`에서 일별/주별/월별 통계 집계
2. `user_achievements`에서 달성한 업적 조회

## 샘플 데이터 구조

### 플로깅 세션 예시
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-uuid",
  "start_time": "2024-01-15T09:00:00Z",
  "end_time": "2024-01-15T09:30:00Z",
  "duration": 1800,
  "distance": 2.5,
  "average_speed": 5.0,
  "calories_burned": 150,
  "trash_collected": 5,
  "route_data": {
    "points": [
      {"lat": 37.5665, "lng": 126.9780, "timestamp": "2024-01-15T09:00:00Z"},
      {"lat": 37.5670, "lng": 126.9785, "timestamp": "2024-01-15T09:01:00Z"}
    ]
  }
}
```

### 쓰레기 수집 기록 예시
```json
{
  "id": "trash-uuid",
  "session_id": "session-uuid",
  "user_id": "user-uuid",
  "trash_type": "플라스틱",
  "quantity": 2,
  "latitude": 37.5665,
  "longitude": 126.9780,
  "location_name": "한강공원",
  "photo_url": "/images/PlasticWaste.jpg",
  "collected_at": "2024-01-15T09:15:00Z"
}
```

이 데이터베이스 구조는 플로깅 앱의 모든 기능을 지원하며, 확장 가능하고 성능이 최적화되어 있습니다.

## 구현 시 고려사항

1. **실시간 GPS 추적**: `route_points` 테이블에 배치 삽입으로 성능 최적화
2. **이미지 저장**: Supabase Storage를 활용한 쓰레기 사진 저장
3. **통계 계산**: 트리거 함수를 활용한 자동 통계 업데이트
4. **캐싱**: 자주 조회되는 통계 데이터는 Redis 등으로 캐싱
5. **데이터 압축**: 오래된 GPS 포인트는 압축하여 저장 공간 절약