import { useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';
import { useAuthStore } from '@/stores/authStore';
import { useSessionStore } from '@/stores/sessionStore';
import { getSessions, getStats, getDailyTip } from '@/services/api';
import ScoreRing from '@/components/features/ScoreRing';
import { formatDate, formatDuration, getScoreColor } from '@/utils/formatters';
import { DrivingSession } from '@/types';

function SessionCard({ session }: { session: DrivingSession }) {
  const scoreColor = getScoreColor(session.score);
  return (
    <View style={styles.sessionCard}>
      <View style={styles.sessionThumb}>
        <MaterialCommunityIcons name="car-side" size={22} color={Colors.primary.container} />
      </View>
      <View style={styles.sessionInfo}>
        <Text style={styles.sessionTitle} numberOfLines={1}>{session.title}</Text>
        <Text style={styles.sessionMeta}>
          {formatDate(session.startedAt)} · {formatDuration(session.durationMinutes)}
        </Text>
      </View>
      <View style={styles.sessionScoreCol}>
        <Text style={[styles.sessionScoreNum, { color: scoreColor }]}>{session.score}</Text>
        <Text style={styles.sessionScoreLabel}>{session.scoreLabel}</Text>
      </View>
    </View>
  );
}

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const user = useAuthStore((s) => s.user);
  const {
    dashcamConnected,
    sessions,
    stats,
    dailyTip,
    setSessions,
    setStats,
    setDailyTip,
  } = useSessionStore();

  const firstName = (user?.name ?? '').split(' ')[0] || 'User';

  useEffect(() => {
    if (!user) return;
    getSessions(user.id).then(setSessions).catch(() => {});
    getStats(user.id).then(setStats).catch(() => {});
    getDailyTip().then(setDailyTip).catch(() => {});
  }, [user?.id]);

  const lastSession = sessions[0] ?? null;
  const currentScore = stats?.currentScore ?? 4.5;
  const tipText =
    dailyTip?.content ??
    'Maintaining a 3-second gap from the car ahead reduces harsh braking by 40%.';

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.logoRow}>
          <View style={styles.logoMini}>
            <MaterialCommunityIcons name="chip" size={18} color="#fff" />
          </View>
          <Text style={styles.logoText}>Tamakkan</Text>
        </View>
        <View style={styles.headerRight}>
          <TouchableOpacity hitSlop={8}>
            <Text style={styles.langToggle}>EN</Text>
          </TouchableOpacity>
          {dashcamConnected && (
            <View style={styles.avatar}>
              <MaterialCommunityIcons name="account" size={22} color={Colors.primary.container} />
            </View>
          )}
        </View>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 24 }]}
        showsVerticalScrollIndicator={false}
      >
        {/* Greeting */}
        <View style={styles.greeting}>
          <View style={styles.greetingRow}>
            <Text style={styles.greetingName}>Hello, {firstName}!</Text>
            {dashcamConnected && (
              <View style={styles.connectedBadge}>
                <MaterialCommunityIcons name="video" size={13} color={Colors.secondary.onContainer} />
                <Text style={styles.connectedBadgeText}>Connected</Text>
              </View>
            )}
          </View>
          <Text style={styles.subtitle}>
            {dashcamConnected
              ? 'Ready for your next safe journey?'
              : 'Ready for your driving session?'}
          </Text>
        </View>

        {dashcamConnected ? (
          <>
            {/* ── CONNECTED STATE ─────────────────── */}

            {/* Start Driving button */}
            <TouchableOpacity
              onPress={() => router.push('/session')}
              activeOpacity={0.85}
              style={styles.startBtn}
            >
              <LinearGradient
                colors={[Colors.primary.DEFAULT, Colors.secondary.DEFAULT]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.startBtnGradient}
              >
                <MaterialCommunityIcons name="play-circle" size={24} color="#fff" />
                <Text style={styles.startBtnText}>Start Driving Session</Text>
              </LinearGradient>
            </TouchableOpacity>

            {/* Current Score card */}
            <View style={styles.scoreCard}>
              <View style={styles.scoreCardLeft}>
                <Text style={styles.cardLabel}>CURRENT SCORE</Text>
                <View style={styles.scoreLine}>
                  <Text style={styles.scoreNum}>{currentScore.toFixed(1)}</Text>
                  <Text style={styles.scoreUnit}>/5.0</Text>
                </View>
                <View style={styles.scoreTrend}>
                  <MaterialCommunityIcons name="trending-up" size={16} color={Colors.secondary.DEFAULT} />
                  <Text style={styles.scoreTrendText}>+{stats?.scoreChange ?? 7}% vs last week</Text>
                </View>
              </View>
              <ScoreRing
                score={currentScore}
                maxScore={5}
                size={96}
                strokeWidth={8}
                centerIcon={
                  <MaterialCommunityIcons name="star" size={30} color={Colors.primary.DEFAULT} />
                }
              />
            </View>

            {/* Mini stat cards */}
            <View style={styles.miniCardRow}>
              <View style={styles.miniCard}>
                <View style={[styles.miniCardIcon, { backgroundColor: `${Colors.error.DEFAULT}22` }]}>
                  <MaterialCommunityIcons name="alert" size={20} color={Colors.error.DEFAULT} />
                </View>
                <Text style={styles.miniCardLabel}>MISTAKES</Text>
                <Text style={styles.miniCardNum}>{stats?.totalMistakes ?? 12}</Text>
              </View>
              <View style={styles.miniCard}>
                <View style={[styles.miniCardIcon, { backgroundColor: `${Colors.secondary.DEFAULT}22` }]}>
                  <MaterialCommunityIcons name="shield-check" size={20} color={Colors.secondary.DEFAULT} />
                </View>
                <Text style={styles.miniCardLabel}>SAFE POINTS</Text>
                <Text style={styles.miniCardNum}>{stats?.safePoints ?? 340}</Text>
              </View>
            </View>

            {/* Top improvement area */}
            <View style={styles.improvementCard}>
              <View style={styles.improvementIcon}>
                <MaterialCommunityIcons name="home-alert" size={22} color={Colors.primary.fixed} />
              </View>
              <View style={styles.improvementContent}>
                <Text style={styles.improvementLabel}>TOP IMPROVEMENT AREA</Text>
                <Text style={styles.improvementTitle}>{stats?.topImprovementArea ?? 'Harsh Braking'}</Text>
              </View>
              <MaterialCommunityIcons name="chevron-right" size={22} color="rgba(255,255,255,0.4)" />
            </View>

            {/* Daily tip */}
            <View style={styles.tipCard}>
              <View style={styles.tipHeader}>
                <MaterialCommunityIcons name="lightbulb-on" size={18} color={Colors.primary.onContainer} />
                <Text style={styles.tipLabel}>DAILY DRIVING TIP</Text>
              </View>
              <Text style={styles.tipText}>{tipText}</Text>
              <View style={styles.tipGlow} />
            </View>

            {/* Last Session */}
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Last Session</Text>
              <TouchableOpacity
                hitSlop={8}
                onPress={() => router.push('/(tabs)/progress')}
                style={styles.viewAllRow}
              >
                <Text style={styles.viewAllText}>VIEW ALL</Text>
                <MaterialCommunityIcons name="arrow-right" size={14} color={Colors.primary.container} />
              </TouchableOpacity>
            </View>

            {lastSession && (
              <View style={styles.lastSessionCard}>
                <LinearGradient
                  colors={['#1e2e2e', '#0a1818']}
                  style={StyleSheet.absoluteFillObject}
                >
                  <View style={styles.lastSessionBgIcon}>
                    <MaterialCommunityIcons name="car-side" size={64} color="rgba(255,255,255,0.08)" />
                  </View>
                </LinearGradient>
                <View style={styles.lastSessionPlayOverlay}>
                  <View style={styles.lastSessionPlayBtn}>
                    <MaterialCommunityIcons name="play" size={28} color="#fff" />
                  </View>
                </View>
                <LinearGradient
                  colors={['transparent', 'rgba(0,0,0,0.82)']}
                  style={styles.lastSessionInfoOverlay}
                >
                  <View style={styles.lastSessionInfoRow}>
                    <View>
                      <Text style={styles.lastSessionTitle}>{lastSession.title}</Text>
                      <Text style={styles.lastSessionMeta}>
                        {formatDate(lastSession.startedAt)} · {formatDuration(lastSession.durationMinutes)}
                      </Text>
                    </View>
                    <View style={styles.lastSessionBadge}>
                      <Text style={styles.lastSessionBadgeText}>{lastSession.score} pts</Text>
                    </View>
                  </View>
                </LinearGradient>
              </View>
            )}
          </>
        ) : (
          <>
            {/* ── PRE-CONNECT STATE ─────────────────── */}

            {/* DashCam status card */}
            <View style={styles.dashcamCard}>
              <View style={styles.dashcamIconWrap}>
                <View style={styles.dashcamIconRing} />
                <MaterialCommunityIcons name="video-off" size={44} color={Colors.primary.container} />
              </View>
              <Text style={styles.dashcamTitle}>No DashCam Detected</Text>
              <Text style={styles.dashcamDesc}>
                Connect your device via Bluetooth or Wi-Fi to start recording your driving metrics.
              </Text>
              <TouchableOpacity
                onPress={() => router.push('/(tabs)/devices')}
                activeOpacity={0.85}
                style={styles.connectBtn}
              >
                <LinearGradient
                  colors={[Colors.primary.DEFAULT, Colors.secondary.DEFAULT]}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.connectBtnGradient}
                >
                  <MaterialCommunityIcons name="connection" size={22} color="#fff" />
                  <Text style={styles.connectBtnText}>Connect to DashCam</Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>

            {/* Stats row */}
            <View style={styles.statsRow}>
              <View style={styles.statCard}>
                <View style={styles.statBadge}>
                  <Text style={[styles.statBadgeText, { color: Colors.secondary.onContainer }]}>
                    LAST SCORE
                  </Text>
                </View>
                <View style={styles.statNumRow}>
                  <Text style={[styles.statNum, { color: Colors.primary.DEFAULT }]}>
                    {stats?.lastScore ?? 88}
                  </Text>
                  <Text style={styles.statUnit}>/100</Text>
                </View>
                <Text style={styles.statSub}>Great lane discipline</Text>
              </View>
              <View style={styles.statCard}>
                <View style={[styles.statBadge, { backgroundColor: `${Colors.tertiary.DEFAULT}18` }]}>
                  <Text style={[styles.statBadgeText, { color: Colors.tertiary.DEFAULT }]}>
                    TRAINING
                  </Text>
                </View>
                <View style={styles.statNumRow}>
                  <Text style={[styles.statNum, { color: Colors.tertiary.DEFAULT }]}>
                    {stats?.trainingHours ?? 14.5}
                  </Text>
                  <Text style={styles.statUnit}>hrs</Text>
                </View>
                <Text style={styles.statSub}>{stats?.sessionsThisWeek ?? 4} sessions this week</Text>
              </View>
            </View>

            {/* Recommended Focus card */}
            <View style={styles.focusCard}>
              <View style={styles.focusHeader}>
                <Text style={styles.focusTitle}>Recommended Focus</Text>
                <MaterialCommunityIcons name="lightbulb-on" size={22} color={Colors.primary.onContainer} />
              </View>
              <View style={styles.focusPills}>
                <View style={styles.focusPill}>
                  <Text style={styles.focusPillText}>Smooth Braking</Text>
                </View>
                <View style={styles.focusPill}>
                  <Text style={styles.focusPillText}>Speed Consistency</Text>
                </View>
              </View>
              <Text style={styles.focusDesc}>
                Your last 3 sessions indicate a tendency for harsh braking at intersections.
              </Text>
            </View>

            {/* Recent Sessions */}
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Recent Sessions</Text>
              <TouchableOpacity hitSlop={8} onPress={() => router.push('/(tabs)/progress')}>
                <Text style={styles.viewAllText}>VIEW ALL</Text>
              </TouchableOpacity>
            </View>

            {sessions.length > 0
              ? sessions.slice(0, 3).map((s) => <SessionCard key={s.id} session={s} />)
              : (
                <View style={styles.emptyState}>
                  <Text style={styles.emptyStateText}>Loading sessions…</Text>
                </View>
              )}
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  // ── Header ──
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    height: 60,
    backgroundColor: '#ffffff',
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  logoMini: {
    width: 30,
    height: 30,
    borderRadius: 8,
    backgroundColor: Colors.primary.DEFAULT,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: {
    fontSize: 15,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  langToggle: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
  },
  avatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: `${Colors.primary.container}22`,
    borderWidth: 2,
    borderColor: Colors.primary.container,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // ── Scroll ──
  scroll: {
    paddingHorizontal: 20,
    paddingTop: 24,
    gap: 16,
  },
  // ── Greeting ──
  greeting: {
    gap: 4,
  },
  greetingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap',
  },
  greetingName: {
    fontSize: 28,
    fontWeight: '700',
    color: Colors.surface.on,
  },
  connectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: `${Colors.secondary.container}55`,
    borderRadius: 999,
  },
  connectedBadgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.secondary.onContainer,
  },
  subtitle: {
    fontSize: 16,
    color: Colors.surface.onVariant,
  },
  // ── CONNECTED: Start button ──
  startBtn: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  startBtnGradient: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  startBtnText: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
  },
  // ── CONNECTED: Score card ──
  scoreCard: {
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 24,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  scoreCardLeft: {
    gap: 6,
  },
  cardLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.surface.onVariant,
    letterSpacing: 0.5,
  },
  scoreLine: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 4,
  },
  scoreNum: {
    fontSize: 40,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
    lineHeight: 44,
  },
  scoreUnit: {
    fontSize: 16,
    color: Colors.surface.onVariant,
  },
  scoreTrend: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  scoreTrendText: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.secondary.DEFAULT,
  },
  // ── CONNECTED: Mini cards ──
  miniCardRow: {
    flexDirection: 'row',
    gap: 12,
  },
  miniCard: {
    flex: 1,
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 24,
    padding: 20,
    gap: 8,
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  miniCardIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  miniCardLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.surface.onVariant,
    letterSpacing: 0.5,
  },
  miniCardNum: {
    fontSize: 24,
    fontWeight: '700',
    color: Colors.surface.on,
  },
  // ── CONNECTED: Improvement card ──
  improvementCard: {
    backgroundColor: Colors.surface.inverse,
    borderRadius: 24,
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  improvementIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: 'rgba(255,255,255,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  improvementContent: {
    flex: 1,
    gap: 4,
  },
  improvementLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.6)',
    letterSpacing: 0.5,
  },
  improvementTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  // ── CONNECTED: Tip card ──
  tipCard: {
    backgroundColor: Colors.primary.container,
    borderRadius: 24,
    padding: 20,
    gap: 12,
    overflow: 'hidden',
  },
  tipHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  tipLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.primary.onContainer,
    letterSpacing: 0.5,
    opacity: 0.85,
  },
  tipText: {
    fontSize: 15,
    fontWeight: '500',
    color: Colors.primary.onContainer,
    lineHeight: 22,
  },
  tipGlow: {
    position: 'absolute',
    right: -32,
    bottom: -32,
    width: 128,
    height: 128,
    borderRadius: 64,
    backgroundColor: 'rgba(255,255,255,0.1)',
  },
  // ── CONNECTED: Last session ──
  lastSessionCard: {
    borderRadius: 24,
    overflow: 'hidden',
    height: 192,
  },
  lastSessionBgIcon: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  lastSessionPlayOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
  },
  lastSessionPlayBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  lastSessionInfoOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 16,
    paddingBottom: 16,
    paddingTop: 48,
  },
  lastSessionInfoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  lastSessionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#fff',
  },
  lastSessionMeta: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.75)',
    marginTop: 2,
  },
  lastSessionBadge: {
    backgroundColor: Colors.primary.DEFAULT,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
  },
  lastSessionBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#fff',
  },
  // ── PRE-CONNECT: DashCam card ──
  dashcamCard: {
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    gap: 16,
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  dashcamIconWrap: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: Colors.surface.containerLow,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dashcamIconRing: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: 48,
    borderWidth: 3,
    borderColor: Colors.primary.fixed,
    borderStyle: 'dashed',
    opacity: 0.7,
  },
  dashcamTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: Colors.surface.on,
    textAlign: 'center',
  },
  dashcamDesc: {
    fontSize: 14,
    color: Colors.outline.DEFAULT,
    textAlign: 'center',
    lineHeight: 20,
  },
  connectBtn: {
    borderRadius: 16,
    overflow: 'hidden',
    width: '100%',
  },
  connectBtnGradient: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  connectBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  // ── PRE-CONNECT: Stats row ──
  statsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 24,
    padding: 20,
    gap: 8,
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  statBadge: {
    backgroundColor: `${Colors.secondary.container}55`,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    alignSelf: 'flex-start',
  },
  statBadgeText: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  statNumRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 2,
  },
  statNum: {
    fontSize: 32,
    fontWeight: '700',
    lineHeight: 36,
  },
  statUnit: {
    fontSize: 14,
    color: Colors.outline.DEFAULT,
  },
  statSub: {
    fontSize: 13,
    color: Colors.surface.onVariant,
  },
  // ── PRE-CONNECT: Focus card ──
  focusCard: {
    backgroundColor: Colors.primary.container,
    borderRadius: 24,
    padding: 20,
    gap: 12,
  },
  focusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  focusTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: Colors.primary.onContainer,
  },
  focusPills: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  focusPill: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
  },
  focusPillText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
    letterSpacing: 0.3,
  },
  focusDesc: {
    fontSize: 13,
    color: `${Colors.primary.onContainer}CC`,
    lineHeight: 18,
  },
  // ── Shared: Section header + sessions ──
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: Colors.surface.on,
  },
  viewAllRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  viewAllText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.primary.container,
    letterSpacing: 0.5,
  },
  sessionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 20,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: Colors.surface.container,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  sessionThumb: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: `${Colors.primary.container}20`,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sessionInfo: {
    flex: 1,
    gap: 3,
  },
  sessionTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: Colors.surface.on,
  },
  sessionMeta: {
    fontSize: 13,
    color: Colors.outline.DEFAULT,
  },
  sessionScoreCol: {
    alignItems: 'flex-end',
    gap: 2,
  },
  sessionScoreNum: {
    fontSize: 20,
    fontWeight: '700',
  },
  sessionScoreLabel: {
    fontSize: 9,
    fontWeight: '600',
    color: Colors.outline.DEFAULT,
    letterSpacing: 0.5,
  },
  emptyState: {
    paddingVertical: 32,
    alignItems: 'center',
  },
  emptyStateText: {
    fontSize: 14,
    color: Colors.outline.DEFAULT,
  },
});
