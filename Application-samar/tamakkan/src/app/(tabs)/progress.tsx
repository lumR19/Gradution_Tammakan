import React, { useState } from 'react';
import { View, Text, ScrollView, Pressable } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSessionStore } from '../../stores/sessionStore';
import { SessionCard } from '../../components/features/SessionCard';
import { Badge } from '../../components/ui/Badge';
import { getScoreColor } from '../../utils';

const FILTERS = ['All', 'Excellent', 'Good', 'Improving'] as const;
type Filter = typeof FILTERS[number];

export default function ProgressScreen() {
  const insets = useSafeAreaInsets();
  const sessions = useSessionStore((s) => s.sessions);
  const stats = useSessionStore((s) => s.stats);
  const [filter, setFilter] = useState<Filter>('All');

  const filtered = sessions.filter((s) => {
    if (filter === 'All') return true;
    return s.status === filter.toLowerCase();
  });

  const avgScore =
    sessions.length > 0
      ? (sessions.reduce((acc, s) => acc + s.score / s.maxScore, 0) / sessions.length) * 5
      : 0;

  return (
    <View style={{ flex: 1, backgroundColor: '#f7fafa' }}>
      {/* Header */}
      <View
        style={{
          backgroundColor: '#ffffff',
          paddingTop: insets.top + 8,
          paddingHorizontal: 24,
          paddingBottom: 16,
          shadowColor: '#008080',
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.06,
          shadowRadius: 12,
          elevation: 4,
        }}
      >
        <Text style={{ fontSize: 28, fontWeight: '700', color: '#181c1d' }}>Progress</Text>
        <Text style={{ fontSize: 16, color: '#3e4949', marginTop: 2 }}>
          {sessions.length} sessions tracked
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 24, paddingBottom: 24 }}
        showsVerticalScrollIndicator={false}
      >
        {/* Summary card */}
        <View
          style={{
            backgroundColor: '#008080',
            borderRadius: 24,
            padding: 24,
            marginBottom: 24,
            flexDirection: 'row',
            justifyContent: 'space-around',
          }}
        >
          {[
            { label: 'Avg Score', value: avgScore.toFixed(1), unit: '/5.0' },
            { label: 'Sessions', value: String(sessions.length), unit: 'total' },
            { label: 'This Week', value: String(stats.sessionsThisWeek), unit: 'sessions' },
          ].map((item) => (
            <View key={item.label} style={{ alignItems: 'center' }}>
              <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 2 }}>
                <Text
                  style={{ fontSize: 28, fontWeight: '700', color: '#e3fffe' }}
                >
                  {item.value}
                </Text>
                <Text style={{ fontSize: 14, color: 'rgba(255,255,255,0.7)' }}>{item.unit}</Text>
              </View>
              <Text
                style={{
                  fontSize: 12,
                  fontWeight: '600',
                  letterSpacing: 0.5,
                  color: 'rgba(255,255,255,0.7)',
                  textTransform: 'uppercase',
                  marginTop: 4,
                }}
              >
                {item.label}
              </Text>
            </View>
          ))}
        </View>

        {/* Score trend line (simplified visual) */}
        <View
          style={{
            backgroundColor: '#ffffff',
            borderRadius: 24,
            padding: 20,
            marginBottom: 24,
            shadowColor: '#008080',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.06,
            shadowRadius: 12,
            elevation: 3,
          }}
        >
          <Text style={{ fontSize: 16, fontWeight: '600', color: '#181c1d', marginBottom: 16 }}>
            Score Trend
          </Text>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8, height: 80 }}>
            {sessions.slice(0, 7).reverse().map((s, i) => {
              const pct = s.score / s.maxScore;
              const barH = Math.max(16, pct * 72);
              const color = getScoreColor(s.score, s.maxScore);
              return (
                <View
                  key={s.id}
                  style={{ flex: 1, alignItems: 'center', justifyContent: 'flex-end', height: 80 }}
                >
                  <View
                    style={{
                      width: '100%',
                      height: barH,
                      backgroundColor: color,
                      borderRadius: 6,
                      opacity: i === sessions.slice(0, 7).length - 1 ? 1 : 0.5,
                    }}
                  />
                </View>
              );
            })}
          </View>
          <Text style={{ fontSize: 12, color: '#6e7979', marginTop: 8, textAlign: 'center' }}>
            Last {Math.min(sessions.length, 7)} sessions
          </Text>
        </View>

        {/* Filter chips */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={{ gap: 8, paddingBottom: 16 }}
        >
          {FILTERS.map((f) => (
            <Pressable
              key={f}
              onPress={() => setFilter(f)}
              style={{
                paddingHorizontal: 16,
                paddingVertical: 8,
                borderRadius: 999,
                backgroundColor: filter === f ? '#008080' : '#ffffff',
                borderWidth: 1,
                borderColor: filter === f ? '#008080' : '#bdc9c8',
              }}
            >
              <Text
                style={{
                  fontSize: 14,
                  fontWeight: '600',
                  color: filter === f ? '#ffffff' : '#3e4949',
                }}
              >
                {f}
              </Text>
            </Pressable>
          ))}
        </ScrollView>

        {/* Session list */}
        <View style={{ gap: 12 }}>
          {filtered.length === 0 ? (
            <View style={{ alignItems: 'center', paddingVertical: 48 }}>
              <MaterialCommunityIcons name="car-off" size={48} color="#bdc9c8" />
              <Text style={{ fontSize: 16, color: '#6e7979', marginTop: 12 }}>
                No sessions found
              </Text>
            </View>
          ) : (
            filtered.map((session) => (
              <SessionCard key={session.id} session={session} compact onPress={() => {}} />
            ))
          )}
        </View>
      </ScrollView>
    </View>
  );
}
