import { create } from 'zustand';
import type { DrivingSession, DrivingStats, DrivingTip, DashcamDevice } from '../types';
import {
  getSessions,
  getStats,
  getDailyTip,
  startSession as apiStart,
  stopSession as apiStop,
  connectDashcam,
  MOCK_STATS,
  MOCK_SESSIONS,
  MOCK_TIPS,
} from '../services/api';

interface SessionState {
  dashcamConnected: boolean;
  dashcamDevice: DashcamDevice | null;
  activeSessionId: string | null;
  sessions: DrivingSession[];
  stats: DrivingStats;
  dailyTip: DrivingTip;
  isLoading: boolean;

  connectDashcam: (ssid: string) => Promise<void>;
  disconnectDashcam: () => void;
  startSession: () => Promise<void>;
  stopSession: () => Promise<void>;
  fetchSessions: () => Promise<void>;
  fetchStats: () => Promise<void>;
  fetchDailyTip: () => Promise<void>;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  dashcamConnected: false,
  dashcamDevice: null,
  activeSessionId: null,
  sessions: MOCK_SESSIONS,
  stats: MOCK_STATS,
  dailyTip: MOCK_TIPS[0],
  isLoading: false,

  connectDashcam: async (ssid) => {
    set({ isLoading: true });
    await connectDashcam(ssid);
    set({
      dashcamConnected: true,
      isLoading: false,
      dashcamDevice: {
        id: 'cam_001',
        name: 'Tamakkan DashCam',
        ssid,
        connected: true,
        firmwareVersion: '2.4.1',
        batteryLevel: 87,
      },
    });
  },

  disconnectDashcam: () =>
    set({ dashcamConnected: false, dashcamDevice: null }),

  startSession: async () => {
    const id = await apiStart();
    set({ activeSessionId: id });
  },

  stopSession: async () => {
    const { activeSessionId, sessions } = get();
    if (!activeSessionId) return;
    const finished = await apiStop(activeSessionId);
    set({ activeSessionId: null, sessions: [finished, ...sessions] });
  },

  fetchSessions: async () => {
    const data = await getSessions();
    set({ sessions: data });
  },

  fetchStats: async () => {
    const data = await getStats();
    set({ stats: data });
  },

  fetchDailyTip: async () => {
    const data = await getDailyTip();
    set({ dailyTip: data });
  },
}));
