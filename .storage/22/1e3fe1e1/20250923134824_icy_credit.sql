/*
  # 플로깅 세션 테이블 생성

  1. New Tables
    - `plogging_sessions`
      - `id` (uuid, primary key)
      - `user_id` (uuid, references user_profiles)
      - `title` (text)
      - `start_time` (timestamp)
      - `end_time` (timestamp)
      - `duration_seconds` (integer)
      - `distance_km` (numeric)
      - `trash_collected` (integer, default 0)
      - `calories_burned` (integer, default 0)
      - `average_pace` (numeric, nullable)
      - `average_speed` (numeric, nullable)
      - `route_data` (jsonb, nullable - GPS coordinates)
      - `notes` (text, nullable)
      - `weather` (text, nullable)
      - `created_at` (timestamp)

  2. Security
    - Enable RLS on `plogging_sessions` table
    - Add policies for users to manage their own sessions
*/

CREATE TABLE IF NOT EXISTS plogging_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES user_profiles(id) ON DELETE CASCADE NOT NULL,
  title text NOT NULL,
  start_time timestamptz NOT NULL,
  end_time timestamptz,
  duration_seconds integer DEFAULT 0,
  distance_km numeric DEFAULT 0,
  trash_collected integer DEFAULT 0,
  calories_burned integer DEFAULT 0,
  average_pace numeric,
  average_speed numeric,
  route_data jsonb,
  notes text,
  weather text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE plogging_sessions ENABLE ROW LEVEL SECURITY;

-- Users can manage their own sessions
CREATE POLICY "Users can read own sessions"
  ON plogging_sessions
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions"
  ON plogging_sessions
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions"
  ON plogging_sessions
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions"
  ON plogging_sessions
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Function to update user profile stats when session is added/updated
CREATE OR REPLACE FUNCTION update_user_stats_on_session_change()
RETURNS TRIGGER AS $$
BEGIN
  -- Update user profile with aggregated stats
  UPDATE user_profiles SET
    total_distance = (
      SELECT COALESCE(SUM(distance_km), 0)
      FROM plogging_sessions
      WHERE user_id = COALESCE(NEW.user_id, OLD.user_id)
    ),
    total_trash_collected = (
      SELECT COALESCE(SUM(trash_collected), 0)
      FROM plogging_sessions
      WHERE user_id = COALESCE(NEW.user_id, OLD.user_id)
    ),
    total_sessions = (
      SELECT COUNT(*)
      FROM plogging_sessions
      WHERE user_id = COALESCE(NEW.user_id, OLD.user_id)
    ),
    total_calories = (
      SELECT COALESCE(SUM(calories_burned), 0)
      FROM plogging_sessions
      WHERE user_id = COALESCE(NEW.user_id, OLD.user_id)
    ),
    updated_at = now()
  WHERE id = COALESCE(NEW.user_id, OLD.user_id);
  
  RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Triggers to update user stats
CREATE TRIGGER update_user_stats_on_session_insert
  AFTER INSERT ON plogging_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_user_stats_on_session_change();

CREATE TRIGGER update_user_stats_on_session_update
  AFTER UPDATE ON plogging_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_user_stats_on_session_change();

CREATE TRIGGER update_user_stats_on_session_delete
  AFTER DELETE ON plogging_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_user_stats_on_session_change();