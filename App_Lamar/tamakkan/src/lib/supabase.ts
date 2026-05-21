import { createClient } from '@supabase/supabase-js';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const supabase = createClient(
  'https://oxbdnvasnvqlpsadqxuk.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im94YmRudmFzbnZxbHBzYWRxeHVrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyMjgwMTEsImV4cCI6MjA5NDgwNDAxMX0.NHt3h1iEK-1-KZ9hiS0RiLhGjXKKQmr0M6OHZbgUhiY',
  {
    auth: {
      storage: AsyncStorage,
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false,
    },
  },
);
