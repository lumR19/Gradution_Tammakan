import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  Pressable,
  Image,
  Linking,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useSessionStore } from '../../stores/sessionStore';
import { Card } from '../../components/ui/Card';

const DASHCAM_IMAGE =
  'https://lh3.googleusercontent.com/aida-public/AB6AXuAq182mjMjlVQQ8Zrb20K-P9TvWlfO4tkFWkcASRRw7o88fdNHgb0y1iWQIA7hK-C4wlQBjYAf247rppVgXvXhGljr_vvEkYbNfg0fOf-dbiSBQ0OIWpebA802kFC0yMkYHnfMkBwSj7R5Sum7EAC3ckt38m8XNm1xDhYuTZD0BeVNWaBCjVfLnVg-uI8NX6V4-uh-ptqVc7gvIcCWklX1fZ5xJWpUjdeeRYd8e57kVyp54-Fa4ABhhTkCy2ftI1w5VFx__OQTYuqs';

const SETUP_STEPS = [
  {
    step: 1,
    title: 'Power On Device',
    description: "Plug the DashCam into your vehicle's power outlet and wait for the status LED to blink blue.",
    icon: 'power-plug' as const,
  },
  {
    step: 2,
    title: 'Enable Wi-Fi Mode',
    description: "Press the 'Wi-Fi' button on the side of the device until you hear the \"Hotspot Active\" voice prompt.",
    icon: 'access-point' as const,
  },
  {
    step: 3,
    title: 'Join Network',
    description: 'Look for a Wi-Fi network named Tamakkan_Cam_XXXX in your phone settings and connect to it.',
    icon: 'wifi' as const,
  },
];

export default function DevicesScreen() {
  const insets = useSafeAreaInsets();
  const { dashcamConnected, dashcamDevice, connectDashcam, disconnectDashcam } = useSessionStore();
  const [connecting, setConnecting] = useState(false);

  async function handleConnect() {
    setConnecting(true);
    await connectDashcam('Tamakkan_Cam_A1B2');
    setConnecting(false);
  }

  function handleDisconnect() {
    Alert.alert('Disconnect DashCam', 'Are you sure you want to disconnect?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Disconnect', style: 'destructive', onPress: disconnectDashcam },
    ]);
  }

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
        <Text style={{ fontSize: 28, fontWeight: '700', color: '#181c1d' }}>
          {dashcamConnected ? 'My DashCam' : 'Connect DashCam'}
        </Text>
        <Text style={{ fontSize: 16, color: '#3e4949', marginTop: 2 }}>
          {dashcamConnected
            ? 'Your device is active and recording.'
            : 'Follow these steps to link your device.'}
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 24, paddingBottom: 120 }}
        showsVerticalScrollIndicator={false}
      >
        {dashcamConnected && dashcamDevice ? (
          /* Connected state */
          <View style={{ gap: 16 }}>
            <View
              style={{
                backgroundColor: '#ffffff',
                borderRadius: 24,
                padding: 24,
                shadowColor: '#008080',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.06,
                shadowRadius: 12,
                elevation: 3,
              }}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
                <View
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: 16,
                    backgroundColor: 'rgba(128,249,202,0.2)',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <MaterialCommunityIcons name="video" size={32} color="#006c4f" />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 18, fontWeight: '600', color: '#181c1d' }}>
                    {dashcamDevice.name}
                  </Text>
                  <Text style={{ fontSize: 14, color: '#3e4949', marginTop: 2 }}>
                    {dashcamDevice.ssid}
                  </Text>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4 }}>
                    <View
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 4,
                        backgroundColor: '#006c4f',
                      }}
                    />
                    <Text style={{ fontSize: 12, fontWeight: '600', color: '#006c4f' }}>
                      CONNECTED
                    </Text>
                  </View>
                </View>
              </View>

              <View
                style={{
                  marginTop: 20,
                  paddingTop: 16,
                  borderTopWidth: 1,
                  borderTopColor: '#f1f4f4',
                  flexDirection: 'row',
                  justifyContent: 'space-around',
                }}
              >
                {[
                  { label: 'Firmware', value: dashcamDevice.firmwareVersion ?? '—' },
                  { label: 'Battery', value: `${dashcamDevice.batteryLevel ?? '—'}%` },
                  { label: 'Signal', value: 'Strong' },
                ].map((item) => (
                  <View key={item.label} style={{ alignItems: 'center' }}>
                    <Text style={{ fontSize: 16, fontWeight: '700', color: '#181c1d' }}>
                      {item.value}
                    </Text>
                    <Text
                      style={{
                        fontSize: 12,
                        color: '#6e7979',
                        marginTop: 2,
                        fontWeight: '600',
                        letterSpacing: 0.5,
                        textTransform: 'uppercase',
                      }}
                    >
                      {item.label}
                    </Text>
                  </View>
                ))}
              </View>
            </View>

            <Pressable
              onPress={handleDisconnect}
              style={({ pressed }) => ({
                height: 56,
                borderRadius: 16,
                borderWidth: 1.5,
                borderColor: '#ba1a1a',
                alignItems: 'center',
                justifyContent: 'center',
                opacity: pressed ? 0.7 : 1,
              })}
            >
              <Text style={{ fontSize: 16, fontWeight: '600', color: '#ba1a1a' }}>
                Disconnect Device
              </Text>
            </Pressable>
          </View>
        ) : (
          /* Setup flow */
          <View style={{ gap: 20 }}>
            {/* Hero image */}
            <View
              style={{
                borderRadius: 24,
                overflow: 'hidden',
                aspectRatio: 16 / 9,
                shadowColor: '#008080',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.06,
                shadowRadius: 12,
                elevation: 3,
              }}
            >
              <Image
                source={{ uri: DASHCAM_IMAGE }}
                style={{ width: '100%', height: '100%' }}
                resizeMode="cover"
              />
              <View
                style={{
                  position: 'absolute',
                  inset: 0,
                  backgroundColor: 'rgba(0,40,40,0.2)',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <View
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: 32,
                    backgroundColor: 'rgba(255,255,255,0.9)',
                    alignItems: 'center',
                    justifyContent: 'center',
                    shadowColor: '#000',
                    shadowOffset: { width: 0, height: 4 },
                    shadowOpacity: 0.12,
                    shadowRadius: 10,
                    elevation: 6,
                  }}
                >
                  <MaterialCommunityIcons name="play" size={32} color="#008080" />
                </View>
              </View>
              <View
                style={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  right: 0,
                  padding: 16,
                  backgroundColor: 'rgba(0,0,0,0.4)',
                }}
              >
                <Text style={{ color: '#ffffff', fontSize: 14, fontWeight: '500' }}>
                  Visual Guide: Wi-Fi Setup
                </Text>
              </View>
            </View>

            {/* Steps */}
            <View style={{ gap: 12 }}>
              {SETUP_STEPS.map((item) => (
                <View
                  key={item.step}
                  style={{
                    backgroundColor: '#ffffff',
                    borderRadius: 24,
                    padding: 20,
                    flexDirection: 'row',
                    gap: 16,
                    shadowColor: '#008080',
                    shadowOffset: { width: 0, height: 4 },
                    shadowOpacity: 0.06,
                    shadowRadius: 12,
                    elevation: 3,
                  }}
                >
                  <View
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 20,
                      backgroundColor: '#80f9ca',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Text style={{ fontSize: 18, fontWeight: '700', color: '#007354' }}>
                      {item.step}
                    </Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text
                      style={{ fontSize: 16, fontWeight: '700', color: '#006565', marginBottom: 4 }}
                    >
                      {item.title}
                    </Text>
                    <Text style={{ fontSize: 14, color: '#3e4949', lineHeight: 20 }}>
                      {item.description}
                    </Text>
                  </View>
                </View>
              ))}
            </View>

            {/* Help */}
            <View
              style={{
                padding: 20,
                backgroundColor: '#f1f4f4',
                borderRadius: 24,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderWidth: 1.5,
                borderStyle: 'dashed',
                borderColor: '#93f2f2',
              }}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                <MaterialCommunityIcons name="help-circle-outline" size={24} color="#008080" />
                <Text style={{ fontSize: 14, fontWeight: '500', color: '#004f4f' }}>
                  Need help connecting?
                </Text>
              </View>
              <Text style={{ fontSize: 12, fontWeight: '600', color: '#006565' }}>
                Troubleshoot
              </Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* Sticky connect button */}
      {!dashcamConnected && (
        <View
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            padding: 24,
            backgroundColor: 'rgba(255,255,255,0.92)',
            borderTopWidth: 1,
            borderTopColor: '#f1f4f4',
          }}
        >
          <Pressable
            onPress={handleConnect}
            disabled={connecting}
            style={({ pressed }) => ({
              opacity: pressed || connecting ? 0.8 : 1,
              transform: [{ scale: pressed ? 0.97 : 1 }],
            })}
          >
            <LinearGradient
              colors={['#008080', '#006c4f']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={{
                height: 56,
                borderRadius: 16,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 10,
                shadowColor: '#008080',
                shadowOffset: { width: 0, height: 8 },
                shadowOpacity: 0.25,
                shadowRadius: 16,
                elevation: 6,
              }}
            >
              {connecting ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <>
                  <MaterialCommunityIcons name="wifi" size={22} color="#ffffff" />
                  <Text style={{ fontSize: 18, fontWeight: '600', color: '#ffffff' }}>
                    Connect to Wi-Fi
                  </Text>
                </>
              )}
            </LinearGradient>
          </Pressable>
        </View>
      )}
    </View>
  );
}
