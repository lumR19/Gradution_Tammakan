import { create } from 'zustand';
import { User, UserType } from '../types';
import { setAuthToken } from '../services/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  userType: UserType | null;
  isLoading: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  setUserType: (type: UserType) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  userType: null,
  isLoading: false,

  login: (user, token) => {
    setAuthToken(token);
    set({ user, token, isAuthenticated: true, userType: user.userType });
  },

  logout: () => {
    setAuthToken(null);
    set({ user: null, token: null, isAuthenticated: false, userType: null });
  },

  setUserType: (userType) => set({ userType }),
  setLoading: (isLoading) => set({ isLoading }),
}));
