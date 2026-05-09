import { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated, Easing, Image } from 'react-native';
import { router } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuthStore } from '@/stores/authStore';
import Colors from '@/theme/colors';

export default function Index() {
  const logoScale     = useRef(new Animated.Value(3.8)).current;
  const logoOpacity   = useRef(new Animated.Value(0)).current;
  const screenOpacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.parallel([
      // Snap visible immediately so user sees the big logo
      Animated.timing(logoOpacity, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }),
      // Steady, clearly visible zoom-out over 2s — linear feel so every
      // frame of shrinking is equally visible
      Animated.timing(logoScale, {
        toValue: 1,
        duration: 950,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
    ]).start(() => {
      // Hold at resting size
      setTimeout(() => {
        // Slow, smooth fade out
        Animated.timing(screenOpacity, {
          toValue: 0,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }).start(navigate);
      }, 500);
    });
  }, []);

  const navigate = async () => {
    const isAuthenticated = useAuthStore.getState().isAuthenticated;
    if (isAuthenticated) {
      router.replace('/(tabs)');
      return;
    }
    const seen = await AsyncStorage.getItem('hasSeenOnboarding');
    router.replace(seen ? '/(auth)/user-type' : '/(auth)/splash');
  };

  return (
    <Animated.View style={[styles.container, { opacity: screenOpacity }]}>
      <View style={[styles.glow, { top: -80, left: -80, backgroundColor: Colors.primary.fixed }]} />
      <View style={[styles.glow, { bottom: -80, right: -80, backgroundColor: Colors.secondary.fixed }]} />
      <Animated.View style={{ opacity: logoOpacity, transform: [{ scale: logoScale }] }}>
        <Image
          source={require('../assets/logo_name.png')}
          style={styles.logo}
          resizeMode="contain"
        />
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  glow: {
    position: 'absolute',
    width: 320,
    height: 320,
    borderRadius: 160,
    opacity: 0.1,
  },
  logo: {
    width: 320,
    height: 320,
  },
});
