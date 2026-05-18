import { create } from 'zustand';
import { DrivingSession, DrivingStats, DrivingTip, DashcamDevice } from '../types';

interface SessionState {
  dashcamConnected: boolean;
  dashcamDevice: DashcamDevice | null;
  activeSessionId: string | null;
  sessions: DrivingSession[];
  stats: DrivingStats | null;
  dailyTip: DrivingTip | null;
  isLoadingStats: boolean;
  isLoadingSessions: boolean;

  setDashcamConnected: (connected: boolean, device?: DashcamDevice) => void;
  setSessions: (sessions: DrivingSession[]) => void;
  setStats: (stats: DrivingStats) => void;
  setDailyTip: (tip: DrivingTip) => void;
  startSession: (sessionId: string) => void;
  stopSession: (completedSession?: DrivingSession) => void;
  setLoadingStats: (loading: boolean) => void;
  setLoadingSessions: (loading: boolean) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  dashcamConnected: false,
  dashcamDevice: null,
  activeSessionId: null,
  sessions: [],
  stats: null,
  dailyTip: null,
  isLoadingStats: false,
  isLoadingSessions: false,

  setDashcamConnected: (connected, device) =>
    set({ dashcamConnected: connected, dashcamDevice: device ?? null }),

  setSessions: (sessions) => set({ sessions }),
  setStats: (stats) => set({ stats }),
  setDailyTip: (dailyTip) => set({ dailyTip }),

  startSession: (sessionId) => set({ activeSessionId: sessionId }),

  stopSession: (completedSession) =>
    set((state) => ({
      activeSessionId: null,
      sessions: completedSession
        ? [completedSession, ...state.sessions]
        : state.sessions,
    })),

  setLoadingStats: (isLoadingStats) => set({ isLoadingStats }),
  setLoadingSessions: (isLoadingSessions) => set({ isLoadingSessions }),
}));
