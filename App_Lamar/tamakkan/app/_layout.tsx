import '../global.css';
import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useSettingsStore } from '@/stores/settingsStore';

export default function RootLayout() {
  const { loaded, load } = useSettingsStore();
  useEffect(() => { if (!loaded) load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <StatusBar style="dark" />
        <Stack
          screenOptions={{
            headerShown: false,
            animation: 'slide_from_right',
            contentStyle: { backgroundColor: '#f7fafa' },
          }}
        >
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" options={{ animation: 'fade' }} />
          <Stack.Screen name="wifi-connection" options={{ animation: 'slide_from_bottom' }} />
          <Stack.Screen name="session" options={{ animation: 'slide_from_bottom' }} />
          <Stack.Screen name="trip/[id]" options={{ animation: 'slide_from_right' }} />
          <Stack.Screen name="settings" options={{ animation: 'slide_from_right' }} />
        </Stack>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
