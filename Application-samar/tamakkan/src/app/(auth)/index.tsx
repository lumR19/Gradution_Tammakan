import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  Image,
  Animated,
  Easing,
} from 'react-native';
import { router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

const LOGO_URI =
  'https://lh3.googleusercontent.com/aida/ADBb0uhCH7ghb4fmdcnQlGm2NMUCj9hJ-rtJDFWgAKafPnD4pRwz1xXWZ4G3vhTWO5w9d5M762zv08HTX_QLjz4RnN4urovLeuHaLb7LUyrKSYdzOPb8Ss78kSQYhW3CnYTXXmjqBaXmXMeT9MFiAKv7NTLfmsJO3Sxq_SQHzNCSPEyCLbVUCTlwsyNCv50xb57Jz-blkLhPBOQTRw3sNbxvIyampS2w8f9Ka_BbozRq6QWUtPr3BvF8nDmX9PpgrpWfw5Ko3n7npThTWw';

const CAR_IMAGE_URI =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuDeLjZrEVpiRfKL-KyZok57zLjE7Kt5IaVjXpui8qmsfV96YWCHXMbaTWT4MGOn1i502bmVGhjxkyd4QfxAixPlOiEruCMc6Kuc7o2466WtiJQQ5dXY66m6NGLOMsKUOASl0TGoUkVarnWs54K8LnN0KeYaRmvTrb8CbZgsf4mjBLL6ZidU-6oAtqLewTHiFfqQbty6WUNJ_wATadKlyPT_JuHIu86M4e4svlbSQZYuq4jKfPuQ5FDLBpnVS1XsyOydcyO2-KYTQ2k';

export default function SplashScreen() {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const dot1 = useRef(new Animated.Value(0.3)).current;
  const dot2 = useRef(new Animated.Value(0.3)).current;
  const dot3 = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 600,
      useNativeDriver: true,
    }).start();

    const animateDots = () => {
      Animated.sequence([
        Animated.timing(dot1, { toValue: 1, duration: 300, useNativeDriver: true }),
        Animated.timing(dot1, { toValue: 0.3, duration: 300, useNativeDriver: true }),
      ]).start();
      setTimeout(() => {
        Animated.sequence([
          Animated.timing(dot2, { toValue: 1, duration: 300, useNativeDriver: true }),
          Animated.timing(dot2, { toValue: 0.3, duration: 300, useNativeDriver: true }),
        ]).start();
      }, 200);
      setTimeout(() => {
        Animated.sequence([
          Animated.timing(dot3, { toValue: 1, duration: 300, useNativeDriver: true }),
          Animated.timing(dot3, { toValue: 0.3, duration: 300, useNativeDriver: true }),
        ]).start();
      }, 400);
    };

    const interval = setInterval(animateDots, 900);
    const timer = setTimeout(() => router.replace('/(auth)/user-type'), 2800);

    return () => {
      clearInterval(interval);
      clearTimeout(timer);
    };
  }, []);

  return (
    <View style={{ flex: 1, backgroundColor: '#ffffff' }}>
      <StatusBar style="dark" />

      {/* Background blobs */}
      <View
        style={{
          position: 'absolute',
          top: -96,
          left: -96,
          width: 384,
          height: 384,
          borderRadius: 192,
          backgroundColor: '#93f2f2',
          opacity: 0.1,
        }}
      />
      <View
        style={{
          position: 'absolute',
          bottom: -96,
          right: -96,
          width: 384,
          height: 384,
          borderRadius: 192,
          backgroundColor: '#80f9ca',
          opacity: 0.1,
        }}
      />

      <Animated.View
        style={{
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          paddingHorizontal: 24,
          opacity: fadeAnim,
        }}
      >
        {/* Logo */}
        <View style={{ marginBottom: 32, alignItems: 'center' }}>
          <Image
            source={{ uri: LOGO_URI }}
            style={{ width: 200, height: 80 }}
            resizeMode="contain"
          />
        </View>

        {/* Welcome text */}
        <View style={{ alignItems: 'center', maxWidth: 280, gap: 8, marginBottom: 40 }}>
          <Text style={{ fontSize: 22, fontWeight: '600', color: '#181c1d', textAlign: 'center' }}>
            Welcome to Tamakkan
          </Text>
          <Text style={{ fontSize: 16, color: '#3e4949', textAlign: 'center' }}>
            Smart Driving Assessment
          </Text>
        </View>

        {/* Car image card */}
        <View
          style={{
            width: 256,
            height: 256,
            borderRadius: 32,
            overflow: 'hidden',
            shadowColor: '#000',
            shadowOffset: { width: 0, height: 12 },
            shadowOpacity: 0.15,
            shadowRadius: 20,
            elevation: 10,
          }}
        >
          <Image
            source={{ uri: CAR_IMAGE_URI }}
            style={{ width: '100%', height: '100%' }}
            resizeMode="cover"
          />
          <View
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: 96,
              backgroundColor: 'rgba(0,40,40,0.4)',
            }}
          />
          {/* AI badge */}
          <View
            style={{
              position: 'absolute',
              bottom: 16,
              right: 16,
              backgroundColor: '#ffffff',
              borderRadius: 12,
              padding: 12,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 10,
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 2 },
              shadowOpacity: 0.1,
              shadowRadius: 6,
              elevation: 4,
            }}
          >
            <View
              style={{
                width: 36,
                height: 36,
                borderRadius: 18,
                backgroundColor: '#80f9ca',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Text style={{ fontSize: 16 }}>✦</Text>
            </View>
            <View>
              <Text
                style={{ fontSize: 10, fontWeight: '600', color: '#3e4949', letterSpacing: 0.5 }}
              >
                SAFETY SCORE
              </Text>
              <Text style={{ fontSize: 14, fontWeight: '700', color: '#008080' }}>AI Driven</Text>
            </View>
          </View>
        </View>
      </Animated.View>

      {/* Footer */}
      <View style={{ paddingBottom: 48, alignItems: 'center', gap: 12 }}>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <Animated.View
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: '#008080',
              opacity: dot1,
            }}
          />
          <Animated.View
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: '#008080',
              opacity: dot2,
            }}
          />
          <Animated.View
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: '#008080',
              opacity: dot3,
            }}
          />
        </View>
        <Text style={{ fontSize: 14, color: '#94a3b8' }}>Securing your journey...</Text>
      </View>
    </View>
  );
}
