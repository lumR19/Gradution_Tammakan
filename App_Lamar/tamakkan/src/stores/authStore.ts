import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { User, UserType } from '../types';
import { setAuthToken } from '../services/api';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  userType: UserType | null;
  isLoading: boolean;
  initialize: () => Promise<void>;
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

  initialize: async () => {
    try {
      const token = await SecureStore.getItemAsync(TOKEN_KEY);
      const userJson = await AsyncStorage.getItem(USER_KEY);
      if (token && userJson) {
        const user: User = JSON.parse(userJson);
        setAuthToken(token);
        set({ user, token, isAuthenticated: true, userType: user.userType });
      }
    } catch {
      // proceed unauthenticated
    }
  },

  login: (user, token) => {
    setAuthToken(token);
    // Fire-and-forget — state is set immediately; storage persists for next launch
    SecureStore.setItemAsync(TOKEN_KEY, token).catch(() => {});
    AsyncStorage.setItem(USER_KEY, JSON.stringify(user)).catch(() => {});
    set({ user, token, isAuthenticated: true, userType: user.userType });
  },

  logout: () => {
    setAuthToken(null);
    SecureStore.deleteItemAsync(TOKEN_KEY).catch(() => {});
    AsyncStorage.removeItem(USER_KEY).catch(() => {});
    set({ user: null, token: null, isAuthenticated: false, userType: null });
  },

  setUserType: (userType) => set({ userType }),
  setLoading: (isLoading) => set({ isLoading }),
}));
