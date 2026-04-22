export type UserType = 'individual' | 'trainee' | 'instructor';

export interface User {
  id: string;
  firstName: string;
  lastName: string;
  idNumber: string;
  phone: string;
  email: string;
  userType: UserType;
  avatarUrl?: string;
}

export interface DrivingSession {
  id: string;
  title: string;
  date: string;
  durationMinutes: number;
  score: number;
  maxScore: number;
  status: 'excellent' | 'good' | 'improving' | 'needs-work';
  thumbnailUrl?: string;
  mistakes: Mistake[];
  safePoints: number;
}

export interface Mistake {
  id: string;
  type: MistakeType;
  count: number;
  description: string;
}

export type MistakeType =
  | 'harsh-braking'
  | 'harsh-acceleration'
  | 'speeding'
  | 'lane-departure'
  | 'tailgating'
  | 'phone-use';

export interface DrivingStats {
  currentScore: number;
  maxScore: number;
  scoreChange: number;
  totalMistakes: number;
  safePoints: number;
  topIssue: string;
  trainingHours: number;
  sessionsThisWeek: number;
}

export interface DashcamDevice {
  id: string;
  name: string;
  ssid: string;
  connected: boolean;
  firmwareVersion?: string;
  batteryLevel?: number;
}

export interface DrivingTip {
  id: string;
  text: string;
  category: string;
}

export type RootStackParamList = {
  '(auth)': undefined;
  '(tabs)': undefined;
  'session/live': undefined;
};
