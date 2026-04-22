import React from 'react';
import { View, Text, Image, Pressable } from 'react-native';
import type { DrivingSession } from '../../types';
import { formatDate, formatDuration, getScoreColor, getScoreLabel } from '../../utils';

const PLACEHOLDER_THUMB =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuAhoD8basy8ZDmGNMSbuhES38JHmZQUTfIQSAc3XrairDtGZyswux0YKYgyBgfucemonrzxAzjyYc0hngxnk5fC0NSoE4l3NOWBKNXeJGKSPdGoNTJ1R-xNn0PdPiLY9xRsdLPLWHyB4nx8j0P_X-6otc_jJ6Yh6XYDk3Z9xzuvb6u-X-_xJpEKvzTv8MWbQ3RXAxV969kuCLmbqe21YKfWRtV4QLghR9mhB7dzxXWEpNAwIfNEpu_KW6KY0iCpY-6RR2Gj05Ltez0';

interface SessionCardProps {
  session: DrivingSession;
  onPress?: () => void;
  compact?: boolean;
}

export function SessionCard({ session, onPress, compact = false }: SessionCardProps) {
  const scoreColor = getScoreColor(session.score, session.maxScore);
  const label = getScoreLabel(session.score, session.maxScore);

  if (compact) {
    return (
      <Pressable
        onPress={onPress}
        style={({ pressed }) => ({
          backgroundColor: '#ffffff',
          borderRadius: 20,
          padding: 16,
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderWidth: 1,
          borderColor: '#ebeeee',
          shadowColor: '#008080',
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: 0.04,
          shadowRadius: 6,
          elevation: 2,
          opacity: pressed ? 0.85 : 1,
        })}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
          <View
            style={{
              width: 48,
              height: 48,
              borderRadius: 24,
              backgroundColor: '#e6e9e9',
              overflow: 'hidden',
            }}
          >
            <Image
              source={{ uri: session.thumbnailUrl ?? PLACEHOLDER_THUMB }}
              style={{ width: '100%', height: '100%' }}
              resizeMode="cover"
            />
          </View>
          <View>
            <Text style={{ fontSize: 16, fontWeight: '600', color: '#181c1d' }}>
              {session.title}
            </Text>
            <Text style={{ fontSize: 14, color: '#6e7979' }}>
              {formatDate(session.date)} • {formatDuration(session.durationMinutes)}
            </Text>
          </View>
        </View>
        <View style={{ alignItems: 'flex-end' }}>
          <Text style={{ fontSize: 20, fontWeight: '700', color: scoreColor }}>
            {session.score.toFixed(1)}
          </Text>
          <Text style={{ fontSize: 10, fontWeight: '600', color: '#6e7979', letterSpacing: 0.5 }}>
            {label}
          </Text>
        </View>
      </Pressable>
    );
  }

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => ({
        borderRadius: 24,
        overflow: 'hidden',
        opacity: pressed ? 0.9 : 1,
      })}
    >
      <Image
        source={{ uri: session.thumbnailUrl ?? PLACEHOLDER_THUMB }}
        style={{ width: '100%', height: 192 }}
        resizeMode="cover"
      />
      <View
        style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(0,0,0,0.3)',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <View
          style={{
            width: 56,
            height: 56,
            borderRadius: 28,
            backgroundColor: 'rgba(255,255,255,0.2)',
            alignItems: 'center',
            justifyContent: 'center',
            borderWidth: 1,
            borderColor: 'rgba(255,255,255,0.3)',
          }}
        />
      </View>
      <View
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          padding: 16,
          paddingTop: 32,
          flexDirection: 'row',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
        }}
      >
        <View>
          <Text style={{ color: '#ffffff', fontWeight: '700', fontSize: 14 }}>
            {session.title}
          </Text>
          <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12 }}>
            {formatDate(session.date)} • {formatDuration(session.durationMinutes)}
          </Text>
        </View>
        <View
          style={{
            backgroundColor: '#006565',
            paddingHorizontal: 12,
            paddingVertical: 4,
            borderRadius: 999,
          }}
        >
          <Text style={{ color: '#ffffff', fontWeight: '700', fontSize: 12 }}>
            {session.score.toFixed(1)} Score
          </Text>
        </View>
      </View>
    </Pressable>
  );
}
