import axios from 'axios';
import type { DrivingSession, DrivingStats, DrivingTip, User } from '../types';

// Configurable base URL — swap to Jetson IP when on-device
export const API_BASE_URL = 'http://192.168.43.1:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  // Attach auth token when available
  return config;
});

// --------------- Mock data ---------------

export const MOCK_USER: User = {
  id: 'usr_001',
  firstName: 'Ahmed',
  lastName: 'Al-Ghamdi',
  idNumber: '1098765432',
  phone: '+966501234567',
  email: 'ahmed@example.com',
  userType: 'individual',
  avatarUrl: undefined,
};

export const MOCK_STATS: DrivingStats = {
  currentScore: 4.5,
  maxScore: 5.0,
  scoreChange: 7,
  totalMistakes: 12,
  safePoints: 340,
  topIssue: 'Harsh Braking',
  trainingHours: 14.5,
  sessionsThisWeek: 4,
};

export const MOCK_SESSIONS: DrivingSession[] = [
  {
    id: 'ses_142',
    title: 'Session #142',
    date: '2024-10-24T17:30:00',
    durationMinutes: 24,
    score: 4.2,
    maxScore: 5.0,
    status: 'good',
    mistakes: [
      { id: 'e1', type: 'harsh-braking', count: 3, description: 'Sudden stops at intersections' },
    ],
    safePoints: 310,
  },
  {
    id: 'ses_141',
    title: 'Evening Practice',
    date: '2024-10-24T18:00:00',
    durationMinutes: 45,
    score: 4.6,
    maxScore: 5.0,
    status: 'excellent',
    mistakes: [],
    safePoints: 380,
  },
  {
    id: 'ses_140',
    title: 'City Traffic Run',
    date: '2024-10-22T09:15:00',
    durationMinutes: 32,
    score: 3.8,
    maxScore: 5.0,
    status: 'improving',
    mistakes: [
      { id: 'e2', type: 'lane-departure', count: 2, description: 'Lane drift on highway' },
      { id: 'e3', type: 'speeding', count: 1, description: 'Speed above limit' },
    ],
    safePoints: 220,
  },
  {
    id: 'ses_139',
    title: 'Morning Commute',
    date: '2024-10-20T07:45:00',
    durationMinutes: 28,
    score: 4.4,
    maxScore: 5.0,
    status: 'good',
    mistakes: [
      { id: 'e4', type: 'harsh-braking', count: 1, description: 'Emergency stop' },
    ],
    safePoints: 350,
  },
];

export const MOCK_TIPS: DrivingTip[] = [
  {
    id: 'tip_1',
    text: 'Maintaining a 3-second gap from the car ahead reduces harsh braking by 40%.',
    category: 'Safety Distance',
  },
  {
    id: 'tip_2',
    text: 'Check your mirrors every 5–8 seconds to maintain full situational awareness.',
    category: 'Awareness',
  },
  {
    id: 'tip_3',
    text: 'Smooth, gradual acceleration reduces fuel consumption and wear on the drivetrain.',
    category: 'Fuel Efficiency',
  },
];

// --------------- API functions (fall back to mock when offline) ---------------

export async function login(idNumber: string, password: string): Promise<User> {
  try {
    const res = await api.post<User>('/auth/login', { idNumber, password });
    return res.data;
  } catch {
    // Mock: accept any credentials
    if (idNumber.length === 10) return MOCK_USER;
    throw new Error('Invalid credentials');
  }
}

export async function getSessions(): Promise<DrivingSession[]> {
  try {
    const res = await api.get<DrivingSession[]>('/sessions');
    return res.data;
  } catch {
    return MOCK_SESSIONS;
  }
}

export async function getStats(): Promise<DrivingStats> {
  try {
    const res = await api.get<DrivingStats>('/stats');
    return res.data;
  } catch {
    return MOCK_STATS;
  }
}

export async function getDailyTip(): Promise<DrivingTip> {
  try {
    const res = await api.get<DrivingTip>('/tips/daily');
    return res.data;
  } catch {
    return MOCK_TIPS[Math.floor(Math.random() * MOCK_TIPS.length)];
  }
}

export async function connectDashcam(ssid: string): Promise<boolean> {
  try {
    await api.post('/dashcam/connect', { ssid });
    return true;
  } catch {
    return true; // Mock: always succeeds
  }
}

export async function startSession(): Promise<string> {
  try {
    const res = await api.post<{ sessionId: string }>('/sessions/start');
    return res.data.sessionId;
  } catch {
    return `ses_live_${Date.now()}`;
  }
}

export async function stopSession(sessionId: string): Promise<DrivingSession> {
  try {
    const res = await api.post<DrivingSession>(`/sessions/${sessionId}/stop`);
    return res.data;
  } catch {
    return MOCK_SESSIONS[0];
  }
}
