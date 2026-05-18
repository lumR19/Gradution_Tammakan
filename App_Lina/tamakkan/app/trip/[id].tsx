import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';
import { DrivingSession, Mistake } from '@/types';
import { formatDate, formatDuration, getScoreColor } from '@/utils/formatters';
import { getTripCache } from '@/utils/tripCache';
import { useAuthStore } from '@/stores/authStore';

type IconName = React.ComponentProps<typeof MaterialCommunityIcons>['name'];

const MISTAKE_ICONS: Record<string, IconName> = {
  harsh_braking: 'car-brake-alert',
  harsh_acceleration: 'speedometer',
  lane_departure: 'road-variant',
  speeding: 'car-speed-limiter',
  tailgating: 'car-multiple',
  phone_use: 'cellphone',
  drowsiness: 'sleep',
};

const SEVERITY_COLOR: Record<string, string> = {
  low: Colors.tertiary.DEFAULT,
  medium: '#c47900',
  high: Colors.error.DEFAULT,
};

function MistakeRow({ mistake }: { mistake: Mistake }) {
  const icon = MISTAKE_ICONS[mistake.type] ?? 'alert-circle-outline';
  const color = SEVERITY_COLOR[mistake.severity] ?? Colors.tertiary.DEFAULT;
  const mins = Math.floor(mistake.timestamp / 60);
  const secs = mistake.timestamp % 60;
  const timeStr = `${mins}:${String(secs).padStart(2, '0')}`;

  return (
    <View style={styles.mistakeRow}>
      <View style={[styles.mistakeIcon, { backgroundColor: `${color}18` }]}>
        <MaterialCommunityIcons name={icon} size={18} color={color} />
      </View>
      <View style={styles.mistakeBody}>
        <Text style={styles.mistakeLabel}>{mistake.label}</Text>
        <Text style={styles.mistakeTime}>at {timeStr}</Text>
      </View>
      <View style={[styles.severityPill, { backgroundColor: `${color}22`, borderColor: color }]}>
        <Text style={[styles.severityText, { color }]}>{mistake.severity}</Text>
      </View>
    </View>
  );
}

export default function TripDetailScreen() {
  const insets = useSafeAreaInsets();
  const { id } = useLocalSearchParams<{ id: string }>();
  const userId = useAuthStore((s) => s.user?.id ?? '');

  const [session, setSession] = useState<DrivingSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const cached = await getTripCache(userId);
      const found = cached.find((s) => s.id === id) ?? null;
      setSession(found);
      setLoading(false);
    })();
  }, [id, userId]);

  const scoreColor = session ? getScoreColor(session.score) : Colors.outline.DEFAULT;

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={12}>
          <MaterialCommunityIcons name="arrow-left" size={24} color={Colors.surface.on} />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          Trip Summary
        </Text>
        <View style={{ width: 40 }} />
      </View>

      {loading ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={Colors.primary.DEFAULT} />
        </View>
      ) : !session ? (
        <View style={styles.loadingWrap}>
          <MaterialCommunityIcons name="car-off" size={48} color={Colors.outline.DEFAULT} />
          <Text style={styles.notFoundText}>Trip not found</Text>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.goBack}>Go back</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 24 }]}
          showsVerticalScrollIndicator={false}
        >
          {/* Score hero */}
          <View style={[styles.scoreHero, { borderColor: scoreColor }]}>
            <Text style={styles.heroTitle}>{session.title}</Text>
            <Text style={styles.heroDate}>
              {formatDate(session.startedAt)} · {formatDuration(session.durationMinutes)}
            </Text>
            <View style={styles.scorePill}>
              <Text style={[styles.scoreBig, { color: scoreColor }]}>{session.score}</Text>
              <Text style={[styles.scoreLabel, { color: scoreColor }]}>{session.scoreLabel}</Text>
            </View>
          </View>

          {/* Stats row */}
          <View style={styles.statsRow}>
            <View style={styles.statCell}>
              <MaterialCommunityIcons name="clock-outline" size={20} color={Colors.primary.DEFAULT} />
              <Text style={styles.statValue}>{formatDuration(session.durationMinutes)}</Text>
              <Text style={styles.statCaption}>Duration</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statCell}>
              <MaterialCommunityIcons name="alert-outline" size={20} color={Colors.tertiary.DEFAULT} />
              <Text style={styles.statValue}>{session.mistakes.length}</Text>
              <Text style={styles.statCaption}>Events</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statCell}>
              <MaterialCommunityIcons name="calendar-outline" size={20} color={Colors.secondary.DEFAULT} />
              <Text style={styles.statValue}>{formatDate(session.startedAt)}</Text>
              <Text style={styles.statCaption}>Date</Text>
            </View>
          </View>

          {/* Events section */}
          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Driving Events</Text>
            {session.mistakes.length === 0 ? (
              <View style={styles.noEvents}>
                <MaterialCommunityIcons
                  name="check-circle-outline"
                  size={32}
                  color={Colors.secondary.DEFAULT}
                />
                <Text style={styles.noEventsText}>No events recorded — clean drive!</Text>
              </View>
            ) : (
              session.mistakes.map((m, i) => (
                <React.Fragment key={m.id}>
                  {i > 0 && <View style={styles.divider} />}
                  <MistakeRow mistake={m} />
                </React.Fragment>
              ))
            )}
          </View>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    height: 60,
    backgroundColor: '#fff',
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  backBtn: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: Colors.surface.on,
    flex: 1,
    textAlign: 'center',
  },
  loadingWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  notFoundText: {
    fontSize: 16,
    color: Colors.outline.DEFAULT,
    fontWeight: '500',
  },
  goBack: {
    fontSize: 15,
    color: Colors.primary.DEFAULT,
    fontWeight: '600',
  },
  scroll: {
    paddingHorizontal: 16,
    paddingTop: 20,
    gap: 16,
  },
  // ── Score hero ──
  scoreHero: {
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    gap: 8,
    borderWidth: 1.5,
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 16,
    elevation: 3,
  },
  heroTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: Colors.surface.on,
    textAlign: 'center',
  },
  heroDate: {
    fontSize: 13,
    color: Colors.outline.DEFAULT,
  },
  scorePill: {
    alignItems: 'center',
    marginTop: 8,
  },
  scoreBig: {
    fontSize: 56,
    fontWeight: '800',
    lineHeight: 60,
  },
  scoreLabel: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 1,
  },
  // ── Stats row ──
  statsRow: {
    flexDirection: 'row',
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 20,
    paddingVertical: 16,
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 2,
  },
  statCell: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
  },
  statDivider: {
    width: 1,
    backgroundColor: Colors.surface.containerHigh,
    marginVertical: 4,
  },
  statValue: {
    fontSize: 15,
    fontWeight: '700',
    color: Colors.surface.on,
  },
  statCaption: {
    fontSize: 11,
    color: Colors.outline.DEFAULT,
    fontWeight: '500',
  },
  // ── Events section ──
  sectionCard: {
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 20,
    paddingHorizontal: 18,
    paddingVertical: 16,
    gap: 0,
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.outline.DEFAULT,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  divider: {
    height: 1,
    backgroundColor: Colors.surface.containerHigh,
    marginVertical: 2,
  },
  noEvents: {
    alignItems: 'center',
    paddingVertical: 16,
    gap: 8,
  },
  noEventsText: {
    fontSize: 14,
    color: Colors.secondary.DEFAULT,
    fontWeight: '500',
    textAlign: 'center',
  },
  // ── Mistake row ──
  mistakeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
  },
  mistakeIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  mistakeBody: {
    flex: 1,
    gap: 2,
  },
  mistakeLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.surface.on,
  },
  mistakeTime: {
    fontSize: 12,
    color: Colors.outline.DEFAULT,
  },
  severityPill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    borderWidth: 1,
  },
  severityText: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
});
