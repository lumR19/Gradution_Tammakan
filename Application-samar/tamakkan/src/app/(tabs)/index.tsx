import React, { useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  Pressable,
  Image,
  RefreshControl,
} from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { useAuthStore } from '../../stores/authStore';
import { useSessionStore } from '../../stores/sessionStore';
import { ScoreRing } from '../../components/features/ScoreRing';
import { SessionCard } from '../../components/features/SessionCard';
import { TipCard } from '../../components/features/TipCard';
import { StatCard } from '../../components/features/StatCard';
import { Badge } from '../../components/ui/Badge';

const LOGO_URI =
  'https://lh3.googleusercontent.com/aida/ADBb0uhCH7ghb4fmdcnQlGm2NMUCj9hJ-rtJDFWgAKafPnD4pRwz1xXWZ4G3vhTWO5w9d5M762zv08HTX_QLjz4RnN4urovLeuHaLb7LUyrKSYdzOPb8Ss78kSQYhW3CnYTXXmjqBaXmXMeT9MFiAKv7NTLfmsJO3Sxq_SQHzNCSPEyCLbVUCTlwsyNCv50xb57Jz-blkLhPBOQTRw3sNbxvIyampS2w8f9Ka_BbozRq6QWUtPr3BvF8nDmX9PpgrpWfw5Ko3n7npThTWw';

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const user = useAuthStore((s) => s.user);
  const { dashcamConnected, sessions, stats, dailyTip, fetchStats, fetchSessions, fetchDailyTip, startSession } =
    useSessionStore();
  const [refreshing, setRefreshing] = React.useState(false);

  useEffect(() => {
    fetchStats();
    fetchSessions();
    fetchDailyTip();
  }, []);

  async function onRefresh() {
    setRefreshing(true);
    await Promise.all([fetchStats(), fetchSessions(), fetchDailyTip()]);
    setRefreshing(false);
  }

  async function handleStartSession() {
    if (!dashcamConnected) {
      router.push('/(tabs)/devices');
      return;
    }
    await startSession();
    router.push('/session/live');
  }

  const firstName = user?.firstName ?? 'Ahmed';

  return (
    <View style={{ flex: 1, backgroundColor: '#f7fafa' }}>
      <StatusBar style="dark" />

      {/* Custom top bar */}
      <View
        style={{
          backgroundColor: '#ffffff',
          paddingTop: insets.top,
          paddingHorizontal: 24,
          paddingBottom: 12,
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          shadowColor: '#008080',
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.06,
          shadowRadius: 12,
          elevation: 4,
          zIndex: 10,
        }}
      >
        <Image source={{ uri: LOGO_URI }} style={{ width: 120, height: 40 }} resizeMode="contain" />
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Text style={{ fontSize: 16, fontWeight: '700', color: '#008080' }}>EN</Text>
          <View
            style={{
              width: 40,
              height: 40,
              borderRadius: 20,
              borderWidth: 2,
              borderColor: '#008080',
              backgroundColor: '#e6e9e9',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
            }}
          >
            <MaterialCommunityIcons name="account" size={24} color="#006565" />
          </View>
        </View>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 24, paddingBottom: 24 }}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#008080" />}
      >
        {/* Greeting */}
        <View style={{ marginBottom: 24 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <Text style={{ fontSize: 28, fontWeight: '700', color: '#181c1d' }}>
              Hello, {firstName}!
            </Text>
            <View
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                gap: 6,
                backgroundColor: dashcamConnected ? 'rgba(128,249,202,0.3)' : '#ebeeee',
                paddingHorizontal: 12,
                paddingVertical: 6,
                borderRadius: 999,
              }}
            >
              <MaterialCommunityIcons
                name={dashcamConnected ? 'video' : 'video-off'}
                size={14}
                color={dashcamConnected ? '#007354' : '#6e7979'}
                style={{ fontVariationSettings: "'FILL' 1" }}
              />
              <Text
                style={{
                  fontSize: 12,
                  fontWeight: '600',
                  letterSpacing: 0.5,
                  color: dashcamConnected ? '#007354' : '#6e7979',
                }}
              >
                {dashcamConnected ? 'Connected' : 'Disconnected'}
              </Text>
            </View>
          </View>
          <Text style={{ fontSize: 16, color: '#3e4949' }}>
            {dashcamConnected ? 'Ready for your next safe journey?' : 'Ready for your driving session?'}
          </Text>
        </View>

        {/* Start Driving Button */}
        <Pressable
          onPress={handleStartSession}
          style={({ pressed }) => ({
            marginBottom: 24,
            opacity: pressed ? 0.85 : 1,
            transform: [{ scale: pressed ? 0.98 : 1 }],
          })}
        >
          <LinearGradient
            colors={['#006565', '#006c4f']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={{
              height: 56,
              borderRadius: 16,
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 12,
              shadowColor: '#006565',
              shadowOffset: { width: 0, height: 8 },
              shadowOpacity: 0.2,
              shadowRadius: 20,
              elevation: 6,
            }}
          >
            <MaterialCommunityIcons name="play-circle" size={24} color="#ffffff" />
            <Text style={{ fontSize: 18, fontWeight: '600', color: '#ffffff' }}>
              {dashcamConnected ? 'Start Driving Session' : 'Connect DashCam First'}
            </Text>
          </LinearGradient>
        </Pressable>

        {/* Stats bento grid */}
        <View style={{ gap: 16, marginBottom: 24 }}>
          {/* Score card (full width) */}
          <View
            style={{
              backgroundColor: '#ffffff',
              borderRadius: 24,
              padding: 24,
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              shadowColor: '#008080',
              shadowOffset: { width: 0, height: 4 },
              shadowOpacity: 0.06,
              shadowRadius: 12,
              elevation: 3,
            }}
          >
            <View>
              <Text
                style={{
                  fontSize: 12,
                  fontWeight: '600',
                  letterSpacing: 0.5,
                  color: '#3e4949',
                  textTransform: 'uppercase',
                  marginBottom: 4,
                }}
              >
                CURRENT SCORE
              </Text>
              <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 4 }}>
                <Text style={{ fontSize: 40, fontWeight: '700', color: '#006565', lineHeight: 48 }}>
                  {stats.currentScore.toFixed(1)}
                </Text>
                <Text style={{ fontSize: 16, color: '#3e4949' }}>/{stats.maxScore.toFixed(1)}</Text>
              </View>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 }}>
                <MaterialCommunityIcons name="trending-up" size={16} color="#006c4f" />
                <Text style={{ fontSize: 12, fontWeight: '600', color: '#006c4f' }}>
                  +{stats.scoreChange}% vs last week
                </Text>
              </View>
            </View>
            <ScoreRing score={stats.currentScore} maxScore={stats.maxScore} size={96} />
          </View>

          {/* Mini stat cards */}
          <View style={{ flexDirection: 'row', gap: 16 }}>
            <StatCard
              label="Mistakes"
              value={stats.totalMistakes}
              iconName="alert"
              iconBg="rgba(186,26,26,0.1)"
              iconColor="#ba1a1a"
              subtitle="This week"
            />
            <StatCard
              label="Safe Points"
              value={stats.safePoints}
              iconName="shield-check"
              iconBg="rgba(128,249,202,0.3)"
              iconColor="#006c4f"
              subtitle="Accumulated"
            />
          </View>

          {/* Top improvement card */}
          <View
            style={{
              backgroundColor: '#002020',
              borderRadius: 24,
              padding: 20,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 16,
            }}
          >
            <View
              style={{
                width: 48,
                height: 48,
                borderRadius: 12,
                backgroundColor: 'rgba(255,255,255,0.1)',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <MaterialCommunityIcons name="alert-octagon" size={24} color="#93f2f2" />
            </View>
            <View style={{ flex: 1 }}>
              <Text
                style={{
                  fontSize: 12,
                  fontWeight: '600',
                  letterSpacing: 0.5,
                  color: 'rgba(255,255,255,0.6)',
                  textTransform: 'uppercase',
                  marginBottom: 2,
                }}
              >
                TOP IMPROVEMENT AREA
              </Text>
              <Text style={{ fontSize: 16, fontWeight: '600', color: '#ffffff' }}>
                {stats.topIssue}
              </Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={24} color="rgba(255,255,255,0.4)" />
          </View>
        </View>

        {/* Daily tip */}
        <View style={{ marginBottom: 24 }}>
          <TipCard tip={dailyTip} />
        </View>

        {/* Recent sessions */}
        <View style={{ marginBottom: 8 }}>
          <View
            style={{
              flexDirection: 'row',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 16,
            }}
          >
            <Text style={{ fontSize: 22, fontWeight: '600', color: '#181c1d' }}>Last Session</Text>
            <Pressable onPress={() => router.push('/(tabs)/progress')}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                <Text
                  style={{ fontSize: 12, fontWeight: '600', letterSpacing: 0.5, color: '#006565' }}
                >
                  VIEW ALL
                </Text>
                <MaterialCommunityIcons name="arrow-right" size={16} color="#006565" />
              </View>
            </Pressable>
          </View>

          {sessions.length > 0 && (
            <SessionCard session={sessions[0]} onPress={() => {}} />
          )}
        </View>
      </ScrollView>
    </View>
  );
}
