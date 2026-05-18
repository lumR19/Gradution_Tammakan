export type UserType = 'individual' | 'trainee' | 'instructor';

export interface User {
  id: string;
  name: string;
  nationalId: string;
  phone: string;
  userType: UserType;
  avatarUrl?: string;
  joinedAt: string;
}

export type ScoreLabel = 'EXCELLENT' | 'GOOD' | 'IMPROVING' | 'NEEDS WORK';

export type MistakeType =
  | 'harsh_braking'
  | 'harsh_acceleration'
  | 'lane_departure'
  | 'speeding'
  | 'tailgating'
  | 'phone_use'
  | 'drowsiness';

export interface Mistake {
  id: string;
  type: MistakeType;
  label: string;
  timestamp: number;
  severity: 'low' | 'medium' | 'high';
}

export interface DrivingSession {
  id: string;
  userId: string;
  title: string;
  startedAt: string;
  endedAt?: string;
  durationMinutes: number;
  score: number;
  scoreLabel: ScoreLabel;
  thumbnailUrl?: string;
  mistakes: Mistake[];
  videoUrl?: string;
}

export interface DrivingStats {
  currentScore: number;
  maxScore: number;
  scoreChange: number;
  totalMistakes: number;
  safePoints: number;
  trainingHours: number;
  sessionsThisWeek: number;
  topImprovementArea: string;
  lastScore?: number;
}

export interface DashcamDevice {
  id: string;
  name: string;
  macAddress: string;
  isConnected: boolean;
  batteryLevel?: number;
  firmwareVersion: string;
  lastConnected?: string;
  ssid?: string;
}

export interface DrivingTip {
  id: string;
  content: string;
  category: MistakeType | 'general';
  date: string;
}

export interface LoginPayload {
  nationalId: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  token: string;
}
