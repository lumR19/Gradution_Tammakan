import axios, { AxiosInstance } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  User,
  DrivingSession,
  DrivingStats,
  DashcamDevice,
  DrivingTip,
  AuthResponse,
} from '../types';
import { useSettingsStore } from '../stores/settingsStore';

// Base URL is overridden per-request from useSettingsStore.jetsonIp so that
// REST and WebSocket always point to the same Jetson (one knob, not two).
const api: AxiosInstance = axios.create({
  baseURL: 'http://192.168.1.137:8000', // overridden in interceptor below
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

let _authToken: string | null = null;

export function setAuthToken(token: string | null) {
  _authToken = token;
}

api.interceptors.request.use((config) => {
  // One knob: REST base URL always matches the WS jetsonIp from Settings.
  const { jetsonIp } = useSettingsStore.getState();
  config.baseURL = `http://${jetsonIp}:8000`;
  if (_authToken) {
    config.headers.Authorization = `Bearer ${_authToken}`;
  }
  return config;
});

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_USER: User = {
  id: 'u_001',
  name: 'Ahmed Al-Rashidi',
  nationalId: '1098765432',
  phone: '+966501234567',
  userType: 'individual',
  joinedAt: '2024-01-15T00:00:00Z',
};

const MOCK_SESSIONS: DrivingSession[] = [
  {
    id: 's_001',
    userId: 'u_001',
    title: 'Evening Practice',
    startedAt: '2024-10-24T17:00:00Z',
    endedAt: '2024-10-24T17:45:00Z',
    durationMinutes: 45,
    score: 4.6,
    scoreLabel: 'EXCELLENT',
    mistakes: [],
  },
  {
    id: 's_002',
    userId: 'u_001',
    title: 'City Traffic Run',
    startedAt: '2024-10-22T09:00:00Z',
    endedAt: '2024-10-22T09:32:00Z',
    durationMinutes: 32,
    score: 3.8,
    scoreLabel: 'GOOD',
    mistakes: [
      { id: 'm_001', type: 'tailgating',     label: 'Tailgating',     timestamp: 300, severity: 'high'   },
      { id: 'm_002', type: 'lane_departure',  label: 'Lane Departure', timestamp: 900, severity: 'medium' },
    ],
  },
  {
    id: 's_142',
    userId: 'u_001',
    title: 'Session #142',
    startedAt: '2024-10-21T17:30:00Z',
    endedAt: '2024-10-21T17:54:00Z',
    durationMinutes: 24,
    score: 4.2,
    scoreLabel: 'GOOD',
    mistakes: [],
  },
  {
    id: 's_140',
    userId: 'u_001',
    title: 'Morning Commute',
    startedAt: '2024-10-20T07:00:00Z',
    endedAt: '2024-10-20T07:38:00Z',
    durationMinutes: 38,
    score: 4.4,
    scoreLabel: 'EXCELLENT',
    mistakes: [
      { id: 'm_003', type: 'lane_departure', label: 'Lane Departure', timestamp: 600, severity: 'medium' },
    ],
  },
];

const MOCK_STATS: DrivingStats = {
  currentScore: 4.5,
  maxScore: 5.0,
  scoreChange: 7,
  totalMistakes: 12,
  safePoints: 340,
  trainingHours: 14.5,
  sessionsThisWeek: 4,
  topImprovementArea: 'Harsh Braking',
  lastScore: 4.4,
};

const MOCK_DEVICE: DashcamDevice = {
  id: 'd_001',
  name: 'Tamakkan_Cam_A3F2',
  macAddress: 'AA:BB:CC:DD:EE:FF',
  isConnected: false,
  firmwareVersion: '2.1.4',
  ssid: 'Tamakkan_Cam_A3F2',
};

const MOCK_TIP: DrivingTip = {
  id: 't_001',
  content:
    'Maintaining a 3-second gap from the car ahead significantly reduces tailgating risk.',
  category: 'tailgating',
  date: new Date().toISOString(),
};

// ─── API Functions ────────────────────────────────────────────────────────────

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function login(nationalId: string, password: string): Promise<AuthResponse> {
  try {
    const res = await api.post<AuthResponse>('/auth/login', {
      national_id: nationalId,
      password,
    });
    return res.data;
  } catch {
    await delay(800);
    if (nationalId.length === 10 && password.length >= 6) {
      try {
        const userJson = await AsyncStorage.getItem('mock_registered_user');
        if (userJson) {
          const registered: User = JSON.parse(userJson);
          if (registered.nationalId === nationalId) {
            return { user: registered, token: 'mock_jwt_' + Date.now() };
          }
        }
      } catch {}
      return { user: MOCK_USER, token: 'mock_jwt_' + Date.now() };
    }
    throw new Error('Invalid ID or password');
  }
}

export async function getSessions(userId: string): Promise<DrivingSession[]> {
  try {
    const res = await api.get<DrivingSession[]>(`/sessions/${userId}`);
    return res.data;
  } catch {
    await delay(400);
    return MOCK_SESSIONS;
  }
}

export async function getStats(userId: string): Promise<DrivingStats> {
  try {
    const res = await api.get<DrivingStats>(`/stats/${userId}`);
    return res.data;
  } catch {
    await delay(300);
    return MOCK_STATS;
  }
}

export async function getDailyTip(): Promise<DrivingTip> {
  try {
    const res = await api.get<DrivingTip>('/tips/daily');
    return res.data;
  } catch {
    await delay(200);
    return MOCK_TIP;
  }
}

export async function connectDashcam(deviceId: string): Promise<DashcamDevice> {
  try {
    const res = await api.post<DashcamDevice>('/devices/connect', { device_id: deviceId });
    return res.data;
  } catch {
    await delay(1500);
    return { ...MOCK_DEVICE, id: deviceId, isConnected: true };
  }
}

export async function startSession(deviceId: string): Promise<{ sessionId: string }> {
  try {
    const res = await api.post<{ sessionId: string }>('/sessions/start', {
      device_id: deviceId,
    });
    return res.data;
  } catch {
    await delay(600);
    return { sessionId: 's_' + Date.now() };
  }
}

// ─── Session stop — real backend (BACKEND_SPEC.md §5, §6) ────────────────────

export interface SessionEventDTO {
  event_type: 'lane_departure' | 'tailgating' | 'red_light' | 'near_miss';
  subtype: 'ahead' | 'ran' | null;
  severity: 'medium' | 'high' | 'critical';
  is_vru: boolean;
  session_time_s: number;
  timestamp: number;
}

export interface SessionSummary {
  session_id: string;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
  score: number;
  score_label: 'EXCELLENT' | 'GOOD' | 'IMPROVING' | 'NEEDS WORK';
  event_counts: Record<string, number>;
  events: SessionEventDTO[];
  metadata: { speed_limits_seen?: number[]; model_fps_avg?: number };
}

export async function stopSession(sessionId: string): Promise<SessionSummary | null> {
  try {
    const res = await api.post<SessionSummary>(`/sessions/${sessionId}/stop`);
    return res.data;
  } catch {
    // Backend unreachable — caller falls back to local state.
    return null;
  }
}

export async function getTrips(
  userId: string,
  page = 1,
  pageSize = 10,
): Promise<{ trips: DrivingSession[]; hasMore: boolean }> {
  try {
    const res = await api.get<{ trips: DrivingSession[]; hasMore: boolean }>('/trips', {
      params: { user_id: userId, page, page_size: pageSize },
    });
    return res.data;
  } catch {
    await delay(400);
    const start = (page - 1) * pageSize;
    const slice = MOCK_SESSIONS.slice(start, start + pageSize);
    return { trips: slice, hasMore: start + pageSize < MOCK_SESSIONS.length };
  }
}

export default api;
