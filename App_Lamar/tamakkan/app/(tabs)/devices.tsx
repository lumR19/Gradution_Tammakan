import { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';
import { useSessionStore } from '@/stores/sessionStore';
import { DashcamDevice } from '@/types';

type ConnState = 'idle' | 'connecting' | 'connected';

const STEPS: {
  num: number;
  title: string;
  desc: string;
  highlight?: string;
  suffix?: string;
}[] = [
  {
    num: 1,
    title: 'Power On Device',
    desc: "Plug the DashCam into your vehicle's power outlet and wait for the status LED to blink blue.",
  },
  {
    num: 2,
    title: 'Enable Wi-Fi Mode',
    desc: 'Press the \'Wi-Fi\' button on the side of the device until you hear the "Hotspot Active" voice prompt.',
  },
  {
    num: 3,
    title: 'Join Network',
    desc: 'Look for a Wi-Fi network named ',
    highlight: 'Tamakkan_Cam_XXXX',
    suffix: ' in your phone settings.',
  },
];

export default function DevicesScreen() {
  const insets = useSafeAreaInsets();
  const [connState, setConnState] = useState<ConnState>('idle');
  const setDashcamConnected = useSessionStore((s) => s.setDashcamConnected);

  function handleConnect() {
    if (connState !== 'idle') return;
    setConnState('connecting');

    setTimeout(() => {
      const mockDevice: DashcamDevice = {
        id: 'cam-001',
        name: 'Tamakkan_Cam_A1B2',
        macAddress: 'AA:BB:CC:DD:EE:FF',
        isConnected: true,
        firmwareVersion: '1.2.3',
        lastConnected: new Date().toISOString(),
        ssid: 'Tamakkan_Cam_A1B2',
      };
      setDashcamConnected(true, mockDevice);
      setConnState('connected');

      setTimeout(() => {
        router.navigate('/(tabs)');
      }, 1000);
    }, 2000);
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <TouchableOpacity
            onPress={() => router.navigate('/(tabs)')}
            hitSlop={8}
            style={styles.backBtn}
          >
            <MaterialCommunityIcons name="arrow-left" size={24} color={Colors.primary.container} />
          </TouchableOpacity>
          <View style={styles.logoMini}>
            <MaterialCommunityIcons name="chip" size={18} color="#fff" />
          </View>
          <Text style={styles.logoText}>Tamakkan</Text>
        </View>
        <TouchableOpacity hitSlop={8}>
          <Text style={styles.langToggle}>EN</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 104 }]}
        showsVerticalScrollIndicator={false}
      >
        {/* Headline */}
        <View style={styles.headline}>
          <Text style={styles.headlineTitle}>Connect Your DashCam</Text>
          <Text style={styles.headlineSubtitle}>
            Follow these simple steps to link your device and start tracking your safety metrics.
          </Text>
        </View>

        {/* Hero — video guide placeholder */}
        <View style={styles.heroCard}>
          <LinearGradient
            colors={['#1a3535', '#0a1818']}
            style={StyleSheet.absoluteFillObject}
          />
          <View style={styles.heroBgCam}>
            <MaterialCommunityIcons name="camera" size={96} color="rgba(255,255,255,0.06)" />
          </View>
          <TouchableOpacity activeOpacity={0.8} style={styles.heroPlayBtn}>
            <View style={styles.heroPlayBg} />
            <MaterialCommunityIcons name="play" size={30} color="#fff" />
          </TouchableOpacity>
          <LinearGradient
            colors={['transparent', 'rgba(0,0,0,0.6)']}
            style={styles.heroLabelGrad}
          >
            <View style={styles.heroLabelPill}>
              <MaterialCommunityIcons name="wifi" size={13} color="rgba(255,255,255,0.9)" />
              <Text style={styles.heroLabelText}>Visual Guide: Wi-Fi Setup</Text>
            </View>
          </LinearGradient>
        </View>

        {/* Steps */}
        <View style={styles.steps}>
          {STEPS.map((step) => (
            <View key={step.num} style={styles.stepCard}>
              <View style={styles.stepNum}>
                <Text style={styles.stepNumText}>{step.num}</Text>
              </View>
              <View style={styles.stepBody}>
                <Text style={styles.stepTitle}>{step.title}</Text>
                <Text style={styles.stepDesc}>
                  {step.desc}
                  {step.highlight != null ? (
                    <Text style={styles.stepHighlight}>{step.highlight}</Text>
                  ) : null}
                  {step.suffix ?? ''}
                </Text>
              </View>
            </View>
          ))}
        </View>

        {/* Help */}
        <View style={styles.helpCard}>
          <View style={styles.helpLeft}>
            <MaterialCommunityIcons
              name="help-circle-outline"
              size={22}
              color={Colors.primary.container}
            />
            <Text style={styles.helpText}>Need help connecting?</Text>
          </View>
          <TouchableOpacity hitSlop={8}>
            <Text style={styles.troubleshootBtn}>Troubleshoot</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Sticky bottom button */}
      <View style={[styles.bottomBar, { paddingBottom: Math.max(insets.bottom, 16) }]}>
        <TouchableOpacity
          onPress={handleConnect}
          activeOpacity={connState === 'idle' ? 0.85 : 1}
          style={styles.connectWrap}
          disabled={connState !== 'idle'}
        >
          {connState === 'idle' && (
            <LinearGradient
              colors={[Colors.primary.container, Colors.secondary.DEFAULT]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.connectInner}
            >
              <MaterialCommunityIcons name="wifi" size={22} color="#fff" />
              <Text style={styles.connectText}>Connect to Wi-Fi</Text>
            </LinearGradient>
          )}
          {connState === 'connecting' && (
            <View style={[styles.connectInner, styles.connectingBg]}>
              <ActivityIndicator size="small" color="#fff" />
              <Text style={styles.connectText}>Connecting…</Text>
            </View>
          )}
          {connState === 'connected' && (
            <View style={[styles.connectInner, styles.connectedBg]}>
              <MaterialCommunityIcons name="check-circle" size={22} color="#fff" />
              <Text style={styles.connectText}>Connected!</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>
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
    paddingHorizontal: 16,
    height: 60,
    backgroundColor: '#fff',
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
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
  langToggle: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
    paddingHorizontal: 4,
  },
  // ── Scroll ──
  scroll: {
    paddingHorizontal: 20,
    paddingTop: 24,
    gap: 20,
  },
  // ── Headline ──
  headline: {
    gap: 8,
  },
  headlineTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: Colors.surface.on,
  },
  headlineSubtitle: {
    fontSize: 16,
    color: Colors.surface.onVariant,
    lineHeight: 24,
  },
  // ── Hero card ──
  heroCard: {
    height: 200,
    borderRadius: 24,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 6,
  },
  heroBgCam: {
    position: 'absolute',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroPlayBtn: {
    width: 64,
    height: 64,
    borderRadius: 32,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.4)',
  },
  heroPlayBg: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(255,255,255,0.18)',
  },
  heroLabelGrad: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 14,
    paddingBottom: 14,
    paddingTop: 40,
  },
  heroLabelPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(0,0,0,0.4)',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  heroLabelText: {
    fontSize: 13,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.92)',
  },
  // ── Steps ──
  steps: {
    gap: 12,
  },
  stepCard: {
    backgroundColor: Colors.surface.containerLowest,
    borderRadius: 24,
    padding: 18,
    flexDirection: 'row',
    gap: 14,
    alignItems: 'flex-start',
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 2,
    borderWidth: 1,
    borderColor: Colors.surface.containerLow,
  },
  stepNum: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.secondary.container,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  stepNumText: {
    fontSize: 17,
    fontWeight: '700',
    color: Colors.secondary.onContainer,
  },
  stepBody: {
    flex: 1,
    gap: 4,
    paddingTop: 3,
  },
  stepTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
  },
  stepDesc: {
    fontSize: 14,
    color: Colors.surface.onVariant,
    lineHeight: 20,
  },
  stepHighlight: {
    fontWeight: '600',
    color: Colors.surface.on,
  },
  // ── Help ──
  helpCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.surface.containerLow,
    borderRadius: 24,
    padding: 16,
    borderWidth: 1,
    borderColor: Colors.primary.fixed,
    borderStyle: 'dashed',
  },
  helpLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  helpText: {
    fontSize: 14,
    fontWeight: '500',
    color: Colors.primary.DEFAULT,
  },
  troubleshootBtn: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.primary.DEFAULT,
    letterSpacing: 0.3,
  },
  // ── Bottom sticky ──
  bottomBar: {
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: 'rgba(247,250,250,0.92)',
    borderTopWidth: 1,
    borderTopColor: Colors.surface.container,
  },
  connectWrap: {
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: Colors.primary.container,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.22,
    shadowRadius: 16,
    elevation: 8,
  },
  connectInner: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  connectText: {
    fontSize: 17,
    fontWeight: '600',
    color: '#fff',
  },
  connectingBg: {
    backgroundColor: Colors.outline.DEFAULT,
  },
  connectedBg: {
    backgroundColor: Colors.secondary.DEFAULT,
  },
});
