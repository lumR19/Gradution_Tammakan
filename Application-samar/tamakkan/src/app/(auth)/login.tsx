import React, { useState } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { TopBar } from '../../components/ui/TopBar';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { useAuthStore } from '../../stores/authStore';

export default function LoginScreen() {
  const [tab, setTab] = useState<'login' | 'signup'>('login');
  const [idNumber, setIdNumber] = useState('');
  const [password, setPassword] = useState('');

  const { login, isLoading, error, clearError } = useAuthStore();

  async function handleLogin() {
    clearError();
    if (!idNumber || idNumber.length !== 10) {
      Alert.alert('Validation', 'Please enter a valid 10-digit ID number.');
      return;
    }
    if (!password) {
      Alert.alert('Validation', 'Please enter your password.');
      return;
    }
    await login(idNumber, password);
    const { isAuthenticated } = useAuthStore.getState();
    if (isAuthenticated) {
      router.replace('/(tabs)/');
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={{ flex: 1, backgroundColor: '#f7fafa' }}
    >
      <TopBar />

      <ScrollView
        contentContainerStyle={{ flexGrow: 1, paddingBottom: 40 }}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={{ flex: 1, alignItems: 'center', paddingTop: 32, paddingHorizontal: 24 }}>
          <View style={{ width: '100%', maxWidth: 420 }}>
            {/* Hero branding */}
            <View style={{ alignItems: 'center', marginBottom: 32 }}>
              <View
                style={{
                  width: 80,
                  height: 80,
                  borderRadius: 20,
                  backgroundColor: '#008080',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 20,
                  shadowColor: '#008080',
                  shadowOffset: { width: 0, height: 8 },
                  shadowOpacity: 0.3,
                  shadowRadius: 16,
                  elevation: 8,
                }}
              >
                <MaterialCommunityIcons name="car-emergency" size={44} color="#ffffff" />
              </View>
              <Text style={{ fontSize: 28, fontWeight: '700', color: '#181c1d' }}>
                Welcome Back
              </Text>
              <Text style={{ fontSize: 14, color: '#3e4949', marginTop: 4 }}>
                Log in to track your driving excellence.
              </Text>
            </View>

            {/* Tab switcher */}
            <View
              style={{
                backgroundColor: '#f1f4f4',
                borderRadius: 16,
                padding: 6,
                flexDirection: 'row',
                marginBottom: 24,
              }}
            >
              {(['login', 'signup'] as const).map((t) => (
                <Pressable
                  key={t}
                  onPress={() => {
                    setTab(t);
                    if (t === 'signup') router.push('/(auth)/signup');
                  }}
                  style={{
                    flex: 1,
                    paddingVertical: 12,
                    paddingHorizontal: 16,
                    borderRadius: 12,
                    alignItems: 'center',
                    backgroundColor: tab === t ? '#ffffff' : 'transparent',
                    shadowColor: tab === t ? '#000' : 'transparent',
                    shadowOffset: { width: 0, height: 2 },
                    shadowOpacity: tab === t ? 0.06 : 0,
                    shadowRadius: 4,
                    elevation: tab === t ? 2 : 0,
                  }}
                >
                  <Text
                    style={{
                      fontSize: 16,
                      fontWeight: '600',
                      color: tab === t ? '#008080' : '#3e4949',
                    }}
                  >
                    {t === 'login' ? 'Login' : 'Sign Up'}
                  </Text>
                </Pressable>
              ))}
            </View>

            {/* Error banner */}
            {error ? (
              <View
                style={{
                  backgroundColor: '#ffdad6',
                  borderRadius: 12,
                  padding: 12,
                  marginBottom: 16,
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <MaterialCommunityIcons name="alert-circle" size={18} color="#ba1a1a" />
                <Text style={{ fontSize: 14, color: '#93000a', flex: 1 }}>{error}</Text>
              </View>
            ) : null}

            {/* Form */}
            <View style={{ gap: 16 }}>
              <Input
                label="ID Number"
                iconName="card-account-details"
                placeholder="Enter your 10-digit ID"
                keyboardType="numeric"
                maxLength={10}
                value={idNumber}
                onChangeText={setIdNumber}
              />

              <View>
                <View
                  style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 }}
                >
                  <Text
                    style={{
                      fontSize: 12,
                      fontWeight: '600',
                      letterSpacing: 0.5,
                      color: '#006565',
                      textTransform: 'uppercase',
                      marginLeft: 4,
                    }}
                  >
                    PASSWORD
                  </Text>
                  <Pressable>
                    <Text style={{ fontSize: 12, fontWeight: '600', color: '#006565' }}>
                      Forgot?
                    </Text>
                  </Pressable>
                </View>
                <Input
                  label=""
                  iconName="lock"
                  placeholder="••••••••"
                  secure
                  value={password}
                  onChangeText={setPassword}
                />
              </View>

              <View style={{ marginTop: 8 }}>
                <Button
                  label="Sign In"
                  onPress={handleLogin}
                  loading={isLoading}
                  icon={
                    !isLoading ? (
                      <MaterialCommunityIcons name="login" size={20} color="#ffffff" />
                    ) : undefined
                  }
                />
              </View>
            </View>

            {/* Biometric divider */}
            <View style={{ marginTop: 28 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                <View style={{ flex: 1, height: 1, backgroundColor: '#bdc9c8' }} />
                <Text
                  style={{ fontSize: 12, fontWeight: '600', letterSpacing: 0.5, color: '#6e7979' }}
                >
                  OR SECURE LOGIN WITH
                </Text>
                <View style={{ flex: 1, height: 1, backgroundColor: '#bdc9c8' }} />
              </View>

              <View style={{ flexDirection: 'row', justifyContent: 'center', gap: 16 }}>
                {(['fingerprint', 'face-recognition'] as const).map((icon) => (
                  <Pressable
                    key={icon}
                    style={({ pressed }) => ({
                      padding: 16,
                      backgroundColor: '#ffffff',
                      borderWidth: 1,
                      borderColor: pressed ? '#008080' : '#bdc9c8',
                      borderRadius: 16,
                      opacity: pressed ? 0.85 : 1,
                    })}
                  >
                    <MaterialCommunityIcons
                      name={icon}
                      size={32}
                      color="#6e7979"
                    />
                  </Pressable>
                ))}
              </View>
            </View>
          </View>
        </View>
      </ScrollView>

      {/* Decorative blobs */}
      <View
        style={{
          position: 'absolute',
          bottom: -48,
          left: -48,
          width: 192,
          height: 192,
          borderRadius: 96,
          backgroundColor: '#80f9ca',
          opacity: 0.15,
          zIndex: -1,
        }}
      />
      <View
        style={{
          position: 'absolute',
          top: -48,
          right: -48,
          width: 256,
          height: 256,
          borderRadius: 128,
          backgroundColor: '#93f2f2',
          opacity: 0.1,
          zIndex: -1,
        }}
      />
    </KeyboardAvoidingView>
  );
}
