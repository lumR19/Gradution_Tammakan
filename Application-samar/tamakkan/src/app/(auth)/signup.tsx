import React, { useState } from 'react';
import {
  View,
  Text,
  Pressable,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  Switch,
} from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { TopBar } from '../../components/ui/TopBar';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { useAuthStore } from '../../stores/authStore';
import { validateSaudiId, validateSaudiPhone } from '../../utils';

type RoleTab = 'trainee' | 'instructor';

export default function SignupScreen() {
  const [role, setRole] = useState<RoleTab>('trainee');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [dob, setDob] = useState('');
  const [idNumber, setIdNumber] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSignup() {
    if (!firstName || !lastName || !email || !phone || !password || !idNumber) {
      Alert.alert('Validation', 'Please fill in all required fields.');
      return;
    }
    if (!validateSaudiId(idNumber)) {
      Alert.alert('Validation', 'Please enter a valid 10-digit Saudi ID number.');
      return;
    }
    if (!agreed) {
      Alert.alert('Terms', 'Please agree to the Terms of Service to continue.');
      return;
    }

    setIsLoading(true);
    // Mock: simulate registration
    setTimeout(() => {
      setIsLoading(false);
      router.replace('/(tabs)/');
    }, 1500);
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={{ flex: 1, backgroundColor: '#f7fafa' }}
    >
      <TopBar />

      <ScrollView
        contentContainerStyle={{ paddingBottom: 140, paddingHorizontal: 24, paddingTop: 24 }}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={{ maxWidth: 420, width: '100%', alignSelf: 'center' }}>
          {/* Header */}
          <View style={{ marginBottom: 24 }}>
            <Text style={{ fontSize: 28, fontWeight: '700', color: '#181c1d' }}>
              Create Account
            </Text>
            <Text style={{ fontSize: 16, color: '#3e4949', marginTop: 6, lineHeight: 24 }}>
              Start your journey toward safer driving today.
            </Text>
          </View>

          {/* Role switcher */}
          <View
            style={{
              backgroundColor: '#f1f4f4',
              borderRadius: 12,
              padding: 4,
              flexDirection: 'row',
              marginBottom: 20,
            }}
          >
            {(['trainee', 'instructor'] as const).map((r) => (
              <Pressable
                key={r}
                onPress={() => setRole(r)}
                style={{
                  flex: 1,
                  paddingVertical: 10,
                  borderRadius: 10,
                  alignItems: 'center',
                  backgroundColor: role === r ? '#ffffff' : 'transparent',
                  shadowColor: role === r ? '#000' : 'transparent',
                  shadowOffset: { width: 0, height: 1 },
                  shadowOpacity: role === r ? 0.06 : 0,
                  shadowRadius: 3,
                  elevation: role === r ? 1 : 0,
                }}
              >
                <Text
                  style={{
                    fontSize: 12,
                    fontWeight: '600',
                    letterSpacing: 0.5,
                    color: role === r ? '#006565' : '#3e4949',
                    textTransform: 'uppercase',
                  }}
                >
                  {r}
                </Text>
              </Pressable>
            ))}
          </View>

          {/* Name fields */}
          <View style={{ flexDirection: 'row', gap: 12, marginBottom: 16 }}>
            <View style={{ flex: 1 }}>
              <Input
                label="First Name *"
                placeholder="Ahmed"
                value={firstName}
                onChangeText={setFirstName}
                autoCapitalize="words"
              />
            </View>
            <View style={{ flex: 1 }}>
              <Input
                label="Last Name *"
                placeholder="Al-Ghamdi"
                value={lastName}
                onChangeText={setLastName}
                autoCapitalize="words"
              />
            </View>
          </View>

          <View style={{ gap: 16 }}>
            <Input
              label="Email Address *"
              iconName="email"
              placeholder="ahmed@example.com"
              keyboardType="email-address"
              autoCapitalize="none"
              value={email}
              onChangeText={setEmail}
            />

            <Input
              label="Phone Number *"
              iconName="phone"
              placeholder="+966 5X XXX XXXX"
              keyboardType="phone-pad"
              value={phone}
              onChangeText={setPhone}
            />

            <Input
              label="Password *"
              iconName="lock"
              placeholder="••••••••"
              secure
              value={password}
              onChangeText={setPassword}
            />
          </View>

          {/* Divider */}
          <View
            style={{ borderTopWidth: 1, borderTopColor: '#e6e9e9', marginVertical: 20 }}
          />

          <View style={{ gap: 16 }}>
            <Input
              label="Date of Birth *"
              iconName="calendar-month"
              placeholder="DD / MM / YYYY"
              keyboardType="numeric"
              value={dob}
              onChangeText={setDob}
            />

            <Input
              label="ID Number *"
              iconName="card-account-details"
              placeholder="1XXXXXXXXX"
              keyboardType="numeric"
              maxLength={10}
              value={idNumber}
              onChangeText={setIdNumber}
            />
          </View>

          {/* Terms */}
          <Pressable
            onPress={() => setAgreed((v) => !v)}
            style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 12, marginTop: 20 }}
          >
            <View
              style={{
                width: 22,
                height: 22,
                borderRadius: 6,
                borderWidth: 2,
                borderColor: agreed ? '#008080' : '#bdc9c8',
                backgroundColor: agreed ? '#008080' : 'transparent',
                alignItems: 'center',
                justifyContent: 'center',
                marginTop: 1,
              }}
            >
              {agreed && (
                <MaterialCommunityIcons name="check" size={14} color="#ffffff" />
              )}
            </View>
            <Text style={{ fontSize: 14, color: '#3e4949', flex: 1, lineHeight: 20 }}>
              I agree to the{' '}
              <Text style={{ color: '#006565', fontWeight: '600' }}>Terms of Service</Text>
              {' '}and{' '}
              <Text style={{ color: '#006565', fontWeight: '600' }}>Privacy Policy</Text>.
            </Text>
          </Pressable>
        </View>
      </ScrollView>

      {/* Sticky bottom action */}
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
        <View style={{ maxWidth: 420, alignSelf: 'center', width: '100%' }}>
          <Button label="Sign Up" onPress={handleSignup} loading={isLoading} />
          <Text
            style={{
              textAlign: 'center',
              marginTop: 12,
              fontSize: 14,
              color: '#3e4949',
            }}
          >
            Already have an account?{' '}
            <Text
              style={{ color: '#006565', fontWeight: '700' }}
              onPress={() => router.back()}
            >
              Log In
            </Text>
          </Text>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}
