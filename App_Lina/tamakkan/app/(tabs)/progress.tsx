import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';
import AppLogo from '@/components/AppLogo';
import { useAuthStore } from '@/stores/authStore';
import { getTrips } from '@/services/api';
import { getTripCache, saveTripCache } from '@/utils/tripCache';
import { DrivingSession } from '@/types';
import { formatDate, formatDuration, getScoreColor } from '@/utils/formatters';

const PAGE_SIZE = 10;

function ScoreBadge({ score }: { score: number }) {
  const color = getScoreColor(score);
  return (
    <View style={[styles.scoreBadge, { borderColor: color, backgroundColor: `${color}18` }]}>
      <Text style={[styles.scoreNum, { color }]}>{score}</Text>
    </View>
  );
}

function TripCard({ session, onPress }: { session: DrivingSession; onPress: () => void }) {
  const accentColor = getScoreColor(session.score);
  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.75} style={styles.cardWrap}>
      <View style={[styles.card, { borderLeftColor: accentColor }]}>
        <View style={styles.cardIconWrap}>
          <MaterialCommunityIcons name="car-outline" size={22} color={Colors.primary.DEFAULT} />
        </View>
        <View style={styles.cardBody}>
          <Text style={styles.cardTitle} numberOfLines={1}>{session.title}</Text>
          <View style={styles.cardMeta}>
            <MaterialCommunityIcons name="calendar-outline" size={13} color={Colors.outline.DEFAULT} />
            <Text style={styles.cardMetaText}>{formatDate(session.startedAt)}</Text>
            <Text style={styles.cardMetaDot}>·</Text>
            <MaterialCommunityIcons name="clock-outline" size={13} color={Colors.outline.DEFAULT} />
            <Text style={styles.cardMetaText}>{formatDuration(session.durationMinutes)}</Text>
            {session.mistakes.length > 0 && (
              <>
                <Text style={styles.cardMetaDot}>·</Text>
                <MaterialCommunityIcons name="alert-outline" size={13} color={Colors.tertiary.DEFAULT} />
                <Text style={[styles.cardMetaText, { color: Colors.tertiary.DEFAULT }]}>
                  {session.mistakes.length} event{session.mistakes.length !== 1 ? 's' : ''}
                </Text>
              </>
            )}
          </View>
        </View>
        <View style={styles.cardRight}>
          <ScoreBadge score={session.score} />
          <MaterialCommunityIcons name="chevron-right" size={18} color={Colors.outline.DEFAULT} style={{ marginTop: 4 }} />
        </View>
      </View>
    </TouchableOpacity>
  );
}

function EmptyState() {
  return (
    <View style={styles.emptyWrap}>
      <View style={styles.emptyIcon}>
        <MaterialCommunityIcons name="car-clock" size={48} color={Colors.primary.container} />
      </View>
      <Text style={styles.emptyTitle}>No trips yet</Text>
      <Text style={styles.emptySubtitle}>Complete a driving session to see your history here.</Text>
    </View>
  );
}

export default function ProgressScreen() {
  const insets = useSafeAreaInsets();
  const user = useAuthStore((s) => s.user);
  const userId = user?.id ?? '';

  const [trips, setTrips] = useState<DrivingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const pageRef = useRef(1);
  const fetchingRef = useRef(false);

  const loadFromCache = useCallback(async () => {
    const cached = await getTripCache(userId);
    if (cached.length > 0) setTrips(cached);
  }, [userId]);

  const fetchPage = useCallback(
    async (page: number, append = false) => {
      if (!userId || fetchingRef.current) return;
      fetchingRef.current = true;
      try {
        const { trips: fresh, hasMore: more } = await getTrips(userId, page, PAGE_SIZE);
        setHasMore(more);
        setTrips((prev) => {
          const next = append ? [...prev, ...fresh] : fresh;
          saveTripCache(userId, next);
          return next;
        });
        pageRef.current = page;
      } finally {
        fetchingRef.current = false;
      }
    },
    [userId],
  );

  useEffect(() => {
    (async () => {
      await loadFromCache();
      await fetchPage(1);
      setLoading(false);
    })();
  }, [loadFromCache, fetchPage]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchPage(1);
    setRefreshing(false);
  }, [fetchPage]);

  const onLoadMore = useCallback(async () => {
    if (!hasMore || loadingMore) return;
    setLoadingMore(true);
    await fetchPage(pageRef.current + 1, true);
    setLoadingMore(false);
  }, [hasMore, loadingMore, fetchPage]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.logoRow}>
          <AppLogo size="mini" />
        </View>
        <Text style={styles.langToggle}>EN</Text>
      </View>

      {/* Page title */}
      <View style={styles.titleRow}>
        <Text style={styles.pageTitle}>Trip History</Text>
        {trips.length > 0 && (
          <Text style={styles.tripCount}>{trips.length} trips</Text>
        )}
      </View>

      {loading && trips.length === 0 ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={Colors.primary.DEFAULT} />
        </View>
      ) : (
        <FlatList
          data={trips}
          keyExtractor={(item) => item.id}
          contentContainerStyle={[
            styles.list,
            { paddingBottom: insets.bottom + 24 },
            trips.length === 0 && styles.listEmpty,
          ]}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              colors={[Colors.primary.DEFAULT]}
              tintColor={Colors.primary.DEFAULT}
            />
          }
          onEndReached={onLoadMore}
          onEndReachedThreshold={0.3}
          ListEmptyComponent={<EmptyState />}
          ListFooterComponent={
            loadingMore ? (
              <ActivityIndicator
                color={Colors.primary.DEFAULT}
                style={{ marginVertical: 16 }}
              />
            ) : null
          }
          renderItem={({ item }) => (
            <TripCard
              session={item}
              onPress={() => router.push(`/trip/${item.id}`)}
            />
          )}
        />
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
    paddingHorizontal: 20,
    height: 60,
    backgroundColor: '#fff',
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
  langToggle: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 8,
  },
  pageTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: Colors.surface.on,
  },
  tripCount: {
    fontSize: 13,
    color: Colors.outline.DEFAULT,
    fontWeight: '500',
  },
  loadingWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  list: {
    paddingHorizontal: 16,
    gap: 10,
    paddingTop: 4,
  },
  listEmpty: {
    flex: 1,
  },
  // ── Trip card ──
  cardWrap: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 16,
    padding: 14,
    borderLeftWidth: 4,
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.07,
    shadowRadius: 12,
    elevation: 2,
  },
  cardIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: `${Colors.primary.container}18`,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  cardBody: {
    flex: 1,
    gap: 5,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.surface.on,
  },
  cardMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 3,
  },
  cardMetaText: {
    fontSize: 12,
    color: Colors.outline.DEFAULT,
  },
  cardMetaDot: {
    fontSize: 12,
    color: Colors.outline.variant,
  },
  cardRight: {
    alignItems: 'center',
    gap: 2,
    flexShrink: 0,
  },
  // ── Score badge ──
  scoreBadge: {
    borderRadius: 10,
    borderWidth: 1.5,
    paddingHorizontal: 8,
    paddingVertical: 3,
    minWidth: 44,
    alignItems: 'center',
  },
  scoreNum: {
    fontSize: 16,
    fontWeight: '700',
  },
  // ── Empty state ──
  emptyWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 40,
    gap: 12,
    paddingTop: 48,
  },
  emptyIcon: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: `${Colors.primary.container}18`,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: Colors.surface.on,
  },
  emptySubtitle: {
    fontSize: 14,
    color: Colors.outline.DEFAULT,
    textAlign: 'center',
    lineHeight: 20,
  },
});
