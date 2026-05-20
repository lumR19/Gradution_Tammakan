import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'tamakkan_settings';

export interface AppSettings {
  voiceAlertsEnabled: boolean;
  sensitivity: number; // 0–100
  jetsonIp: string;
  hapticEnabled: boolean;
}

const DEFAULTS: AppSettings = {
  voiceAlertsEnabled: true,
  sensitivity: 50,
  jetsonIp: '192.168.1.137',
  hapticEnabled: true,
};

interface SettingsStore extends AppSettings {
  loaded: boolean;
  load: () => Promise<void>;
  update: (patch: Partial<AppSettings>) => Promise<void>;
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  ...DEFAULTS,
  loaded: false,

  load: async () => {
    try {
      const raw = await AsyncStorage.getItem(STORAGE_KEY);
      if (raw) {
        set({ ...DEFAULTS, ...JSON.parse(raw), loaded: true });
      } else {
        set({ loaded: true });
      }
    } catch {
      set({ loaded: true });
    }
  },

  update: async (patch: Partial<AppSettings>) => {
    set(patch);
    const s = get();
    const toSave: AppSettings = {
      voiceAlertsEnabled: s.voiceAlertsEnabled,
      sensitivity: s.sensitivity,
      jetsonIp: s.jetsonIp,
      hapticEnabled: s.hapticEnabled,
    };
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    } catch {}
  },
}));
