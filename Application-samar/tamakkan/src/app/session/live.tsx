import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  Pressable,
  Animated,
  Alert,
  ScrollView,
} from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { useSessionStore } from '../../stores/sessionStore';

type AlertSeverity = 'info' | 'warning' | 'danger';

interface LiveAlert {
  id: string;
  message: string;
  severity: AlertSeverity;
  timestamp: number;
}

const SEVERITY_COLORS: Record<AlertSeverity, { bg: string; text: string; icon: string }> = {
  info: { bg: 'rgba(0,128,128,0.9)', text: '#e3fffe', icon: 'information' },
  warning: { bg: 'rgba(119,84,0,0.92)', text: '#ffdea8', icon: 'alert' },
  danger: { bg: 'rgba(186,26,26,0.92)', text: '#ffdad6', icon: 'alert-octagon' },
};

const MOCK_ALERTS: Omit<LiveAlert, 'timestamp'>[] = [
  { id: '1', message: 'Maintain safe following distance', severity: 'info' },
  { id: '2', message: 'Harsh braking detected', severity: 'warning' },
  { id: '3', message: 'Speed limit exceeded — 120 km/h zone', severity: 'danger' },
  { id: '4', message: 'Lane departure detected', severity: 'warning' },
  { id: '5', message: 'Good lane keeping — excellent!', severity: 'info' },
];

export default function LiveSessionScreen() {
  const insets = useSafeAreaInsets();
  const { stopSession } = useSessionStore();
  const [elapsed, setElapsed] = useState(0);
  const [currentScore, setCurrentScore] = useState(5.0);
  const [alerts, setAlerts] = useState<LiveAlert[]>([]);
  const [alertIndex, setAlertIndex] = useState(0);
  const alertAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const timerRef = useRef<NodeJS.Timeout>();
  const alertRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    // Recording pulse animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.3, duration: 700, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 700, useNativeDriver: true }),
      ])
    ).start();

    // Elapsed timer
    timerRef.current = setInterval(() => {
      setElapsed((s) => s + 1);
    }, 1000);

    // Mock alert injection
    alertRef.current = setInterval(() => {
      setAlertIndex((i) => {
        const next = i % MOCK_ALERTS.length;
        const alert: LiveAlert = {
          ...MOCK_ALERTS[next],
          timestamp: Date.now(),
        };
        setAlerts((prev) => [alert, ...prev.slice(0, 9)]);
        // Update mock score
        if (alert.severity === 'warning') setCurrentScore((s) => Math.max(3.5, s - 0.1));
        if (alert.severity === 'danger') setCurrentScore((s) => Math.max(3.0, s - 0.2));
        if (alert.severity === 'info') setCurrentScore((s) => Math.min(5.0, s + 0.05));

        Animated.sequence([
          Animated.timing(alertAnim, { toValue: 1, duration: 250, useNativeDriver: true }),
          Animated.delay(2500),
          Animated.timing(alertAnim, { toValue: 0, duration: 250, useNativeDriver: true }),
        ]).start();

        return next + 1;
      });
    }, 4000);

    return () => {
      clearInterval(timerRef.current);
      clearInterval(alertRef.current);
    };
  }, []);

  function formatTime(s: number): string {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  }

  function handleStop() {
    Alert.alert('End Session', 'Stop the current driving session?', [
      { text: 'Continue', style: 'cancel' },
      {
        text: 'End Session',
        style: 'destructive',
        onPress: async () => {
          clearInterval(timerRef.current);
          clearInterval(alertRef.current);
          await stopSession();
          router.replace('/(tabs)/');
        },
      },
    ]);
  }

  const latestAlert = alerts[0];
  const scoreColor =
    currentScore >= 4.5 ? '#76d6d5' : currentScore >= 3.5 ? '#ffba25' : '#ffdad6';

  return (
    <View style={{ flex: 1, backgroundColor: '#0a1a1a' }}>
      <StatusBar style="light" />

      {/* DashCam feed placeholder */}
      <View style={{ position: 'absolute', inset: 0, backgroundColor: '#0d2626' }}>
        <View
          style={{
            flex: 1,
            alignItems: 'center',
            justifyContent: 'center',
            opacity: 0.3,
          }}
        >
          <MaterialCommunityIcons name="video" size={80} color="#76d6d5" />
          <Text style={{ color: '#76d6d5', fontSize: 16, marginTop: 12, fontWeight: '500' }}>
            Live DashCam Feed
          </Text>
        </View>
      </View>

      {/* Top HUD */}
      <View
        style={{
          paddingTop: insets.top + 8,
          paddingHorizontal: 20,
          paddingBottom: 12,
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'rgba(0,0,0,0.5)',
        }}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Animated.View
            style={{
              width: 10,
              height: 10,
              borderRadius: 5,
              backgroundColor: '#ef4444',
              transform: [{ scale: pulseAnim }],
            }}
          />
          <Text style={{ color: '#ffffff', fontSize: 14, fontWeight: '600', letterSpacing: 0.5 }}>
            REC
          </Text>
        </View>

        <View style={{ alignItems: 'center' }}>
          <Text style={{ color: '#ffffff', fontSize: 22, fontWeight: '700', letterSpacing: 2 }}>
            {formatTime(elapsed)}
          </Text>
        </View>

        <Pressable
          onPress={handleStop}
          style={({ pressed }) => ({
            backgroundColor: pressed ? 'rgba(186,26,26,0.8)' : 'rgba(186,26,26,0.6)',
            paddingHorizontal: 16,
            paddingVertical: 8,
            borderRadius: 999,
          })}
        >
          <Text style={{ color: '#ffffff', fontSize: 14, fontWeight: '700' }}>STOP</Text>
        </Pressable>
      </View>

      {/* Score badge */}
      <View style={{ position: 'absolute', top: insets.top + 80, right: 20 }}>
        <View
          style={{
            backgroundColor: 'rgba(0,0,0,0.65)',
            borderRadius: 16,
            padding: 12,
            alignItems: 'center',
            borderWidth: 1.5,
            borderColor: scoreColor,
          }}
        >
          <Text
            style={{ fontSize: 28, fontWeight: '700', color: scoreColor, lineHeight: 32 }}
          >
            {currentScore.toFixed(1)}
          </Text>
          <Text style={{ fontSize: 10, fontWeight: '600', color: 'rgba(255,255,255,0.6)', letterSpacing: 0.5 }}>
            SCORE
          </Text>
        </View>
      </View>

      {/* Live alert banner */}
      {latestAlert && (
        <Animated.View
          style={{
            position: 'absolute',
            top: insets.top + 80,
            left: 20,
            right: 80,
            opacity: alertAnim,
            transform: [{ translateY: alertAnim.interpolate({ inputRange: [0, 1], outputRange: [-8, 0] }) }],
          }}
        >
          <View
            style={{
              backgroundColor: SEVERITY_COLORS[latestAlert.severity].bg,
              borderRadius: 14,
              padding: 14,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <MaterialCommunityIcons
              name={SEVERITY_COLORS[latestAlert.severity].icon as any}
              size={20}
              color={SEVERITY_COLORS[latestAlert.severity].text}
            />
            <Text
              style={{
                fontSize: 14,
                fontWeight: '600',
                color: SEVERITY_COLORS[latestAlert.severity].text,
                flex: 1,
              }}
            >
              {latestAlert.message}
            </Text>
          </View>
        </Animated.View>
      )}

      {/* Bottom panel */}
      <View
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: 'rgba(10,26,26,0.92)',
          borderTopLeftRadius: 28,
          borderTopRightRadius: 28,
          paddingHorizontal: 20,
          paddingTop: 16,
          paddingBottom: insets.bottom + 16,
          maxHeight: 280,
        }}
      >
        <View
          style={{
            width: 40,
            height: 4,
            borderRadius: 2,
            backgroundColor: 'rgba(255,255,255,0.2)',
            alignSelf: 'center',
            marginBottom: 16,
          }}
        />

        <Text
          style={{
            fontSize: 12,
            fontWeight: '600',
            color: 'rgba(255,255,255,0.5)',
            letterSpacing: 0.5,
            textTransform: 'uppercase',
            marginBottom: 12,
          }}
        >
          Live Alerts
        </Text>

        <ScrollView
          showsVerticalScrollIndicator={false}
          style={{ maxHeight: 160 }}
        >
          {alerts.length === 0 ? (
            <Text style={{ color: 'rgba(255,255,255,0.4)', fontSize: 14 }}>
              Monitoring your drive...
            </Text>
          ) : (
            alerts.map((a) => (
              <View
                key={`${a.id}-${a.timestamp}`}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <View
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 4,
                    backgroundColor:
                      a.severity === 'danger'
                        ? '#ef4444'
                        : a.severity === 'warning'
                        ? '#f59e0b'
                        : '#34d399',
                  }}
                />
                <Text style={{ fontSize: 14, color: 'rgba(255,255,255,0.8)', flex: 1 }}>
                  {a.message}
                </Text>
              </View>
            ))
          )}
        </ScrollView>
      </View>
    </View>
  );
}
