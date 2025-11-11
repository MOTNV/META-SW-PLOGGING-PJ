import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});

// Database Types
export interface UserProfile {
  id: string;
  username?: string;
  full_name?: string;
  avatar_url?: string;
  level: number;
  total_distance: number;
  total_trash_collected: number;
  total_sessions: number;
  total_calories: number;
  created_at: string;
  updated_at: string;
}

export interface PloggingSession {
  id: string;
  user_id: string;
  title: string;
  start_time: string;
  end_time?: string;
  duration_seconds: number;
  distance_km: number;
  trash_collected: number;
  calories_burned: number;
  average_pace?: number;
  average_speed?: number;
  route_data?: any;
  notes?: string;
  weather?: string;
  created_at: string;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: string;
  requirement_type: string;
  requirement_value: number;
  points: number;
  created_at: string;
}

export interface UserAchievement {
  id: string;
  user_id: string;
  achievement_id: string;
  unlocked_at?: string;
  progress: number;
  created_at: string;
  achievement?: Achievement;
}

export interface UserGoal {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  goal_type: string;
  target_distance?: number;
  target_trash?: number;
  target_sessions?: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
  completed_at?: string;
  created_at: string;
}

export interface EnvironmentalImpact {
  id: string;
  user_id: string;
  session_id?: string;
  trash_weight_kg: number;
  co2_saved_kg: number;
  plastic_items: number;
  paper_items: number;
  metal_items: number;
  glass_items: number;
  other_items: number;
  location_cleaned?: string;
  before_photo_url?: string;
  after_photo_url?: string;
  created_at: string;
}