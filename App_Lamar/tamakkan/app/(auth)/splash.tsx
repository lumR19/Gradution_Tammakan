import { useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';

export default function SplashScreen() {
  const insets = useSafeAreaInsets();

  useEffect(() => {
    const t = setTimeout(advance, 3000);
    return () => clearTimeout(t);
  }, []);

  const advance = () => router.replace('/(auth)/user-type');

  return (
    <TouchableOpacity activeOpacity={1} onPress={advance} style={styles.container}>
      {/* Decorative glow circles */}
      <View style={[styles.glowTL, { top: -80, left: -80 }]} />
      <View style={[styles.glowBR, { bottom: -80, right: -80 }]} />

      {/* Main content */}
      <View style={styles.content}>
        {/* Logo */}
        <View style={styles.logoWrap}>
          <View style={styles.logoIcon}>
            <MaterialCommunityIcons name="chip" size={40} color="#fff" />
          </View>
          <Text style={styles.logoText}>Tamakkan</Text>
        </View>

        {/* Heading */}
        <View style={styles.headingWrap}>
          <Text style={styles.heading}>Welcome to Tamakkan</Text>
          <Text style={styles.subtitle}>Smart Driving Assessment</Text>
        </View>

        {/* Car image + floating badge */}
        <View style={styles.imageWrap}>
          {/* Dark car placeholder */}
          <View style={styles.carImage}>
            <LinearGradient
              colors={['#1e2e2e', '#0a1818']}
              style={styles.carGradient}
            >
              <MaterialCommunityIcons
                name="car-side"
                size={88}
                color="rgba(255,255,255,0.2)"
              />
              <Text style={styles.safeForWork}>SAFE FOR WORK</Text>
            </LinearGradient>
          </View>

          {/* Floating badge */}
          <View style={styles.badge}>
            <View style={styles.badgeIcon}>
              <MaterialCommunityIcons
                name="shield-star-outline"
                size={20}
                color={Colors.secondary.onContainer}
              />
            </View>
            <View>
              <Text style={styles.badgeLabel}>SAFETY SCORE</Text>
              <Text style={styles.badgeValue}>AI Driven</Text>
            </View>
          </View>
        </View>
      </View>

      {/* Bottom: dots + tagline */}
      <View style={[styles.bottom, { paddingBottom: insets.bottom + 32 }]}>
        <View style={styles.dots}>
          <View style={[styles.dot, { backgroundColor: Colors.primary.container }]} />
          <View style={[styles.dot, { backgroundColor: '#b2dfdb' }]} />
          <View style={[styles.dot, { backgroundColor: '#e0f2f1' }]} />
        </View>
        <Text style={styles.tagline}>Securing your journey...</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  glowTL: {
    position: 'absolute',
    width: 320,
    height: 320,
    borderRadius: 160,
    backgroundColor: Colors.primary.fixed,
    opacity: 0.1,
  },
  glowBR: {
    position: 'absolute',
    width: 320,
    height: 320,
    borderRadius: 160,
    backgroundColor: Colors.secondary.fixed,
    opacity: 0.1,
  },
  content: {
    alignItems: 'center',
    paddingHorizontal: 24,
    gap: 32,
  },
  logoWrap: {
    alignItems: 'center',
    gap: 10,
  },
  logoIcon: {
    width: 80,
    height: 80,
    borderRadius: 20,
    backgroundColor: Colors.primary.DEFAULT,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: Colors.primary.DEFAULT,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 16,
    elevation: 8,
  },
  logoText: {
    fontSize: 22,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
    letterSpacing: 0.5,
  },
  headingWrap: {
    alignItems: 'center',
    gap: 6,
  },
  heading: {
    fontSize: 24,
    fontWeight: '700',
    color: Colors.surface.on,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    fontWeight: '400',
    color: Colors.surface.onVariant,
    textAlign: 'center',
  },
  imageWrap: {
    position: 'relative',
    marginBottom: 24,
  },
  carImage: {
    width: 264,
    height: 264,
    borderRadius: 32,
    overflow: 'hidden',
  },
  carGradient: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  safeForWork: {
    color: 'rgba(255,255,255,0.15)',
    fontSize: 8,
    letterSpacing: 3,
    fontWeight: '600',
  },
  badge: {
    position: 'absolute',
    bottom: -16,
    right: -16,
    backgroundColor: '#ffffff',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
    elevation: 6,
    borderWidth: 1,
    borderColor: '#f0f0f0',
  },
  badgeIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.secondary.container,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeLabel: {
    fontSize: 9,
    fontWeight: '600',
    color: Colors.surface.onVariant,
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  badgeValue: {
    fontSize: 14,
    fontWeight: '700',
    color: Colors.primary.container,
  },
  bottom: {
    position: 'absolute',
    bottom: 0,
    width: '100%',
    alignItems: 'center',
    gap: 12,
  },
  dots: {
    flexDirection: 'row',
    gap: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  tagline: {
    fontSize: 14,
    color: '#94a3b8',
    fontWeight: '400',
  },
});
