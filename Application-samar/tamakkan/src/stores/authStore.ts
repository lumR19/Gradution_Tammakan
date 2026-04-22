import { create } from 'zustand';
import type { User, UserType } from '../types';
import { login as apiLogin } from '../services/api';

interface AuthState {
  isAuthenticated: boolean;
  userType: UserType | null;
  user: User | null;
  isLoading: boolean;
  error: string | null;

  setUserType: (type: UserType) => void;
  login: (idNumber: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  userType: null,
  user: null,
  isLoading: false,
  error: null,

  setUserType: (type) => set({ userType: type }),

  login: async (idNumber, password) => {
    set({ isLoading: true, error: null });
    try {
      const user = await apiLogin(idNumber, password);
      set({ isAuthenticated: true, user, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      set({ isLoading: false, error: message });
    }
  },

  logout: () =>
    set({ isAuthenticated: false, user: null, userType: null, error: null }),

  clearError: () => set({ error: null }),
}));
