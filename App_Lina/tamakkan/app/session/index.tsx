import { useState, useRef, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Alert,
  useWindowDimensions,
} from 'react-native';
import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';
import { useSessionStore } from '@/stores/sessionStore';

// ─── Types ──────────────────────────────────────────────────────────────────
type AlertSeverity = 'danger' | 'warning' | 'safe';

interface AlertEntry {
  id: string;
  message: string;
  severity: AlertSeverity;
  timestamp: number;
}

// ─── Mock data ───────────────────────────────────────────────────────────────
const MOCK_ALERTS: { message: string; severity: AlertSeverity }[] = [
  { message: 'Harsh braking detected', severity: 'danger' },
  { message: 'Lane departure warning', severity: 'warning' },
  { message: 'Following distance too close', severity: 'danger' },
  { message: 'Good lane keeping — 3 sec gap maintained', severity: 'safe' },
  { message: 'Speed limit exceeded in zone', severity: 'warning' },
  { message: 'Safe driving — keep it up!', severity: 'safe' },
  { message: 'Sudden acceleration detected', severity: 'warning' },
  { message: 'Possible drowsiness detected', severity: 'danger' },
  { message: 'Smooth braking — well done', severity: 'safe' },
];

const MOCK_SPEEDS = [60, 80, 80, 120, 60];
const HUD_HEIGHT = 52;
const BANNER_H = 56;

// ─── Helpers ─────────────────────────────────────────────────────────────────
function severityFg(s: AlertSeverity): string {
  // bright enough to be readable on the dark panel
  if (s === 'danger') return Colors.error.container;          // '#ffdad6' light red
  if (s === 'warning') return Colors.tertiary.fixedDim;       // '#ffba25' amber
  return Colors.secondary.fixedDim;                           // '#62dcaf' teal-green
}

function severityAccent(s: AlertSeverity): string {
  if (s === 'danger') return Colors.error.DEFAULT;
  if (s === 'warning') return Colors.tertiary.DEFAULT;
  return Colors.secondary.DEFAULT;
}

function scoreColor(score: number): string {
  if (score >= 4.0) return Colors.primary.DEFAULT;
  if (score >= 3.0) return Colors.tertiary.DEFAULT;
  return Colors.error.DEFAULT;
}

function pad2(n: number): string {
  return n.toString().padStart(2, '0');
}

function formatTime(secs: number): string {
  return `${pad2(Math.floor(secs / 60))}:${pad2(secs % 60)}`;
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function LiveSessionScreen() {
  const insets = useSafeAreaInsets();
  const { height: screenH } = useWindowDimensions();
  const stopSession = useSessionStore((s) => s.stopSession);

  // ── State ──
  const elapsedRef = useRef(0);
  const [elapsed, setElapsed] = useState(0);
  const [score, setScore] = useState(4.2);
  const [alertLog, setAlertLog] = useState<AlertEntry[]>([]);
  const [bannerAlert, setBannerAlert] = useState<AlertEntry | null>(null);
  const [detectedSpeed, setDetectedSpeed] = useState(60);

  // ── Animations ──
  const recPulse = useRef(new Animated.Value(1)).current;
  const bannerY = useRef(new Animated.Value(-BANNER_H)).current;
  const bannerTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const bannerVisibleRef = useRef(false);

  // ── Refs for cycling ──
  const alertIndexRef = useRef(0);
  const speedIndexRef = useRef(0);

  // ── Layout maths ──
  const availH = screenH - insets.top - insets.bottom - HUD_HEIGHT;
  const videoH = availH * 0.56;
  // Banner sits right at the join between video and panel (centred on the edge)
  const bannerTop = insets.top + HUD_HEIGHT + videoH - BANNER_H / 2;

  // ── Banner controller ──
  const showBanner = useCallback(
    (entry: AlertEntry) => {
      setBannerAlert(entry);

      if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current);

      if (!bannerVisibleRef.current) {
        bannerVisibleRef.current = true;
        Animated.spring(bannerY, {
          toValue: 0,
          useNativeDriver: true,
          speed: 22,
          bounciness: 3,
        }).start();
      }

      bannerTimerRef.current = setTimeout(() => {
        Animated.timing(bannerY, {
          toValue: -BANNER_H,
          duration: 220,
          useNativeDriver: true,
        }).start(() => {
          bannerVisibleRef.current = false;
          setBannerAlert(null);
        });
      }, 3000);
    },
    [bannerY],
  );

  // ── REC pulsing ──
  useEffect(() => {
    const anim = Animated.loop(
      Animated.sequence([
        Animated.timing(recPulse, { toValue: 0.08, duration: 550, useNativeDriver: true }),
        Animated.timing(recPulse, { toValue: 1, duration: 550, useNativeDriver: true }),
      ]),
    );
    anim.start();
    return () => anim.stop();
  }, [recPulse]);

  // ── Timer ──
  useEffect(() => {
    const id = setInterval(() => {
      elapsedRef.current += 1;
      setElapsed(elapsedRef.current);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // ── Alert cycling ──
  useEffect(() => {
    function fire() {
      const mock = MOCK_ALERTS[alertIndexRef.current % MOCK_ALERTS.length];
      alertIndexRef.current += 1;
      const entry: AlertEntry = {
        id: String(Date.now()),
        message: mock.message,
        severity: mock.severity,
        timestamp: elapsedRef.current,
      };
      setAlertLog((prev) => [entry, ...prev].slice(0, 20));
      setScore((prev) => {
        const delta =
          entry.severity === 'danger' ? -0.1 : entry.severity === 'warning' ? -0.04 : 0.06;
        return Math.max(1.5, Math.min(5.0, parseFloat((prev + delta).toFixed(1))));
      });
      showBanner(entry);
    }

    const firstId = setTimeout(fire, 1800);
    const id = setInterval(fire, 4500);
    return () => {
      clearTimeout(firstId);
      clearInterval(id);
    };
  }, [showBanner]);

  // ── Speed cycling ──
  useEffect(() => {
    const id = setInterval(() => {
      speedIndexRef.current = (speedIndexRef.current + 1) % MOCK_SPEEDS.length;
      setDetectedSpeed(MOCK_SPEEDS[speedIndexRef.current]);
    }, 9000);
    return () => clearInterval(id);
  }, []);

  // ── Cleanup ──
  useEffect(() => {
    return () => {
      if (bannerTimerRef.current) clearTimeout(bannerTimerRef.current);
    };
  }, []);

  // ── Stop handler ──
  function handleStop() {
    Alert.alert('End Session?', 'Your session data will be saved.', [
      { text: 'Keep Going', style: 'cancel' },
      {
        text: 'End Session',
        style: 'destructive',
        onPress: () => {
          stopSession();
          router.replace('/(tabs)');
        },
      },
    ]);
  }

  const scoreCol = scoreColor(score);

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <StatusBar style="light" />
      {/* ── HUD bar ───────────────────────────────────────────── */}
      <View style={styles.hud}>
        {/* Timer */}
        <Text style={styles.timer}>{formatTime(elapsed)}</Text>

        {/* REC badge */}
        <View style={styles.recBadge}>
          <Animated.View style={[styles.recDot, { opacity: recPulse }]} />
          <Text style={styles.recText}>REC</Text>
        </View>

        {/* Stop button */}
        <TouchableOpacity onPress={handleStop} style={styles.stopBtn} hitSlop={8} activeOpacity={0.75}>
          <MaterialCommunityIcons name="stop-circle" size={15} color="#fff" />
          <Text style={styles.stopText}>STOP</Text>
        </TouchableOpacity>
      </View>

      {/* ── Video area ─────────────────────────────────────────── */}
      <View style={[styles.video, { height: videoH }]}>
        {/* Dark gradient background */}
        <LinearGradient colors={['#0f1e1e', '#1a2e2e']} style={StyleSheet.absoluteFillObject} />

        {/* Grid overlay — subtle tech feel */}
        <View style={styles.gridOverlay} />

        {/* Centred placeholder content */}
        <View style={styles.videoCenter}>
          <MaterialCommunityIcons name="camera" size={52} color="rgba(255,255,255,0.18)" />
          <Text style={styles.videoLabel}>Live DashCam Feed</Text>
          <View style={styles.videoLivePill}>
            <Animated.View style={[styles.recDotSm, { opacity: recPulse }]} />
            <Text style={styles.videoLiveText}>LIVE</Text>
          </View>
        </View>

        {/* Score badge — top-right float */}
        <View style={[styles.scoreBadge, { borderColor: scoreCol }]}>
          <Text style={[styles.scoreBadgeNum, { color: scoreCol }]}>{score.toFixed(1)}</Text>
          <Text style={styles.scoreBadgeUnit}>/5.0</Text>
        </View>

        {/* Speed limit sign — bottom-left float */}
        <View style={styles.speedWrap}>
          <View style={styles.speedSign}>
            <Text style={styles.speedNum}>{detectedSpeed}</Text>
            <Text style={styles.speedUnit}>km/h</Text>
          </View>
          <View style={styles.detectedTag}>
            <Text style={styles.detectedText}>DETECTED</Text>
          </View>
        </View>

        {/* Bottom fade into dark panel */}
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.55)']}
          style={styles.videoFade}
        />
      </View>

      {/* ── Bottom dark panel ─────────────────────────────────── */}
      <View style={[styles.panel, { paddingBottom: Math.max(insets.bottom, 12) }]}>
        {/* Drag handle */}
        <View style={styles.panelHandle} />

        {/* Panel header */}
        <View style={styles.panelHeader}>
          <MaterialCommunityIcons name="alert-circle" size={17} color={Colors.error.container} />
          <Text style={styles.panelTitle}>Live Alerts</Text>
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{alertLog.length}</Text>
          </View>
        </View>

        {/* Alert list */}
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={styles.alertListContent}
          showsVerticalScrollIndicator={false}
        >
          {alertLog.length === 0 ? (
            <View style={styles.emptyState}>
              <MaterialCommunityIcons name="shield-check" size={28} color="rgba(238,241,241,0.25)" />
              <Text style={styles.emptyStateText}>Monitoring your drive…</Text>
            </View>
          ) : (
            alertLog.map((a) => (
              <View key={a.id} style={styles.alertRow}>
                <View style={[styles.alertDot, { backgroundColor: severityFg(a.severity) }]} />
                <Text style={styles.alertRowMsg} numberOfLines={1}>
                  {a.message}
                </Text>
                <Text style={styles.alertRowTime}>{formatTime(a.timestamp)}</Text>
                <View style={[styles.alertChip, { backgroundColor: `${severityAccent(a.severity)}44` }]}>
                  <Text style={[styles.alertChipText, { color: severityFg(a.severity) }]}>
                    {a.severity === 'danger' ? 'DANGER' : a.severity === 'warning' ? 'WARN' : 'SAFE'}
                  </Text>
                </View>
              </View>
            ))
          )}
        </ScrollView>
      </View>

      {/* ── Floating alert banner ─────────────────────────────── */}
      {/* Sits at the video/panel junction, slides in/out vertically */}
      <Animated.View
        style={[
          styles.banner,
          {
            top: bannerTop,
            borderLeftColor: bannerAlert ? severityAccent(bannerAlert.severity) : Colors.error.DEFAULT,
            transform: [{ translateY: bannerY }],
          },
        ]}
      >
        {bannerAlert && (
          <>
            <MaterialCommunityIcons
              name={
                bannerAlert.severity === 'danger'
                  ? 'alert-circle'
                  : bannerAlert.severity === 'warning'
                  ? 'alert'
                  : 'check-circle'
              }
              size={18}
              color={severityFg(bannerAlert.severity)}
            />
            <Text style={styles.bannerMsg} numberOfLines={1}>
              {bannerAlert.message}
            </Text>
            <View style={[styles.bannerChip, { backgroundColor: `${severityAccent(bannerAlert.severity)}44` }]}>
              <Text style={[styles.bannerChipTxt, { color: severityFg(bannerAlert.severity) }]}>
                {bannerAlert.severity === 'danger' ? 'DANGER' : bannerAlert.severity === 'warning' ? 'WARN' : 'SAFE'}
              </Text>
            </View>
          </>
        )}
      </Animated.View>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#0a1212',
  },

  // ── HUD ──
  hud: {
    height: HUD_HEIGHT,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    backgroundColor: '#111e1e',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.06)',
  },
  timer: {
    fontSize: 20,
    fontWeight: '700',
    color: '#fff',
    fontVariant: ['tabular-nums'],
    letterSpacing: 1,
    minWidth: 72,
  },
  recBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 5,
    backgroundColor: 'rgba(186,26,26,0.18)',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(186,26,26,0.4)',
  },
  recDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.error.DEFAULT,
  },
  recText: {
    fontSize: 12,
    fontWeight: '700',
    color: Colors.error.container,
    letterSpacing: 1.5,
  },
  stopBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 14,
    paddingVertical: 7,
    backgroundColor: Colors.error.DEFAULT,
    borderRadius: 10,
    minWidth: 72,
    justifyContent: 'center',
  },
  stopText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: 0.8,
  },

  // ── Video ──
  video: {
    width: '100%',
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  gridOverlay: {
    ...StyleSheet.absoluteFillObject,
    opacity: 0.03,
    borderWidth: 1,
    borderColor: '#fff',
  },
  videoCenter: {
    alignItems: 'center',
    gap: 10,
  },
  videoLabel: {
    fontSize: 14,
    fontWeight: '500',
    color: 'rgba(255,255,255,0.35)',
    letterSpacing: 0.3,
  },
  videoLivePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: 'rgba(186,26,26,0.25)',
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(186,26,26,0.5)',
  },
  recDotSm: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.error.DEFAULT,
  },
  videoLiveText: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.error.container,
    letterSpacing: 2,
  },

  // Score badge
  scoreBadge: {
    position: 'absolute',
    top: 12,
    right: 12,
    backgroundColor: 'rgba(10,18,18,0.82)',
    borderRadius: 14,
    borderWidth: 2,
    paddingHorizontal: 10,
    paddingVertical: 6,
    alignItems: 'center',
  },
  scoreBadgeNum: {
    fontSize: 22,
    fontWeight: '700',
    lineHeight: 26,
  },
  scoreBadgeUnit: {
    fontSize: 10,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.45)',
    marginTop: -2,
  },

  // Speed sign
  speedWrap: {
    position: 'absolute',
    bottom: 14,
    left: 14,
    alignItems: 'center',
    gap: 4,
  },
  speedSign: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#fff',
    borderWidth: 4,
    borderColor: Colors.error.DEFAULT,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.35,
    shadowRadius: 4,
    elevation: 4,
  },
  speedNum: {
    fontSize: 17,
    fontWeight: '900',
    color: '#111',
    lineHeight: 20,
  },
  speedUnit: {
    fontSize: 7,
    fontWeight: '700',
    color: '#444',
    letterSpacing: -0.2,
    lineHeight: 9,
  },
  detectedTag: {
    backgroundColor: Colors.error.DEFAULT,
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 4,
  },
  detectedText: {
    fontSize: 8,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: 0.5,
  },

  // Video fade
  videoFade: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 64,
  },

  // ── Bottom panel ──
  panel: {
    flex: 1,
    backgroundColor: Colors.surface.inverse,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 8,
    paddingHorizontal: 16,
    marginTop: -16,
  },
  panelHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignSelf: 'center',
    marginBottom: 14,
  },
  panelHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  panelTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: '700',
    color: Colors.surface.inverseOn,
  },
  countBadge: {
    minWidth: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: `${Colors.error.DEFAULT}33`,
    paddingHorizontal: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  countText: {
    fontSize: 12,
    fontWeight: '700',
    color: Colors.error.container,
  },

  // Alert list
  alertListContent: {
    gap: 2,
    paddingBottom: 8,
  },
  emptyState: {
    paddingVertical: 24,
    alignItems: 'center',
    gap: 8,
  },
  emptyStateText: {
    fontSize: 13,
    color: 'rgba(238,241,241,0.35)',
    fontWeight: '500',
  },

  // Alert row
  alertRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.05)',
  },
  alertDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    flexShrink: 0,
  },
  alertRowMsg: {
    flex: 1,
    fontSize: 13,
    fontWeight: '500',
    color: Colors.surface.inverseOn,
    lineHeight: 18,
  },
  alertRowTime: {
    fontSize: 11,
    color: 'rgba(238,241,241,0.4)',
    fontWeight: '500',
    fontVariant: ['tabular-nums'],
  },
  alertChip: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 6,
  },
  alertChipText: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.5,
  },

  // ── Floating banner ──
  banner: {
    position: 'absolute',
    left: 12,
    right: 12,
    height: BANNER_H,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: 'rgba(18,28,28,0.95)',
    borderRadius: 16,
    borderLeftWidth: 4,
    paddingHorizontal: 14,
    paddingVertical: 10,
    zIndex: 30,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 12,
    elevation: 10,
  },
  bannerMsg: {
    flex: 1,
    fontSize: 13,
    fontWeight: '600',
    color: Colors.surface.inverseOn,
    lineHeight: 18,
  },
  bannerChip: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  bannerChipTxt: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});
