import React from 'react';
import { View, Text, Pressable, ScrollView, Alert } from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuthStore } from '../../stores/authStore';
import { useSessionStore } from '../../stores/sessionStore';
import { Badge } from '../../components/ui/Badge';

type MenuIcon = keyof typeof MaterialCommunityIcons.glyphMap;

const MENU_SECTIONS: {
  title: string;
  items: { icon: MenuIcon; label: string; value?: string; danger?: boolean; onPress?: () => void }[];
}[] = [
  {
    title: 'Account',
    items: [
      { icon: 'account-edit', label: 'Edit Profile' },
      { icon: 'lock-reset', label: 'Change Password' },
      { icon: 'translate', label: 'Language', value: 'English' },
    ],
  },
  {
    title: 'App',
    items: [
      { icon: 'bell-outline', label: 'Notifications' },
      { icon: 'shield-check-outline', label: 'Privacy Settings' },
      { icon: 'information-outline', label: 'About Tamakkan', value: 'v1.0.0' },
    ],
  },
  {
    title: 'Support',
    items: [
      { icon: 'help-circle-outline', label: 'Help & FAQ' },
      { icon: 'face-agent', label: 'Contact Support' },
    ],
  },
];

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const stats = useSessionStore((s) => s.stats);
  const sessions = useSessionStore((s) => s.sessions);

  function handleLogout() {
    Alert.alert('Log Out', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out',
        style: 'destructive',
        onPress: () => {
          logout();
          router.replace('/(auth)/');
        },
      },
    ]);
  }

  const displayName = user ? `${user.firstName} ${user.lastName}` : 'Ahmed Al-Ghamdi';
  const idNumber = user?.idNumber ?? '1098765432';

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
        <Text style={{ fontSize: 28, fontWeight: '700', color: '#181c1d' }}>Profile</Text>
      </View>

      <ScrollView
        contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 24, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        {/* Profile card */}
        <View
          style={{
            backgroundColor: '#ffffff',
            borderRadius: 24,
            padding: 24,
            marginBottom: 24,
            alignItems: 'center',
            shadowColor: '#008080',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.06,
            shadowRadius: 12,
            elevation: 3,
          }}
        >
          <View
            style={{
              width: 80,
              height: 80,
              borderRadius: 40,
              backgroundColor: '#e6e9e9',
              borderWidth: 3,
              borderColor: '#008080',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16,
            }}
          >
            <MaterialCommunityIcons name="account" size={44} color="#006565" />
          </View>

          <Text style={{ fontSize: 22, fontWeight: '600', color: '#181c1d' }}>{displayName}</Text>
          <Text style={{ fontSize: 14, color: '#6e7979', marginTop: 4 }}>ID: {idNumber}</Text>

          <Badge label="Individual" variant="primary" style={{ marginTop: 12 }} />

          {/* Stats row */}
          <View
            style={{
              flexDirection: 'row',
              justifyContent: 'space-around',
              width: '100%',
              marginTop: 24,
              paddingTop: 20,
              borderTopWidth: 1,
              borderTopColor: '#f1f4f4',
            }}
          >
            {[
              { label: 'Sessions', value: String(sessions.length) },
              { label: 'Avg Score', value: `${stats.currentScore.toFixed(1)}/5` },
              { label: 'Safe Pts', value: String(stats.safePoints) },
            ].map((item) => (
              <View key={item.label} style={{ alignItems: 'center' }}>
                <Text style={{ fontSize: 22, fontWeight: '700', color: '#006565' }}>
                  {item.value}
                </Text>
                <Text
                  style={{
                    fontSize: 12,
                    fontWeight: '600',
                    color: '#6e7979',
                    letterSpacing: 0.5,
                    marginTop: 2,
                    textTransform: 'uppercase',
                  }}
                >
                  {item.label}
                </Text>
              </View>
            ))}
          </View>
        </View>

        {/* Menu sections */}
        {MENU_SECTIONS.map((section) => (
          <View key={section.title} style={{ marginBottom: 24 }}>
            <Text
              style={{
                fontSize: 12,
                fontWeight: '600',
                letterSpacing: 0.5,
                color: '#6e7979',
                textTransform: 'uppercase',
                marginBottom: 10,
                marginLeft: 4,
              }}
            >
              {section.title}
            </Text>
            <View
              style={{
                backgroundColor: '#ffffff',
                borderRadius: 20,
                overflow: 'hidden',
                shadowColor: '#008080',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.06,
                shadowRadius: 12,
                elevation: 3,
              }}
            >
              {section.items.map((item, idx) => (
                <Pressable
                  key={item.label}
                  onPress={item.onPress}
                  style={({ pressed }) => ({
                    flexDirection: 'row',
                    alignItems: 'center',
                    paddingHorizontal: 20,
                    paddingVertical: 16,
                    borderBottomWidth: idx < section.items.length - 1 ? 1 : 0,
                    borderBottomColor: '#f1f4f4',
                    backgroundColor: pressed ? '#f7fafa' : '#ffffff',
                  })}
                >
                  <View
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      backgroundColor: '#f1f4f4',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginRight: 14,
                    }}
                  >
                    <MaterialCommunityIcons
                      name={item.icon}
                      size={20}
                      color={item.danger ? '#ba1a1a' : '#006565'}
                    />
                  </View>
                  <Text
                    style={{
                      flex: 1,
                      fontSize: 16,
                      color: item.danger ? '#ba1a1a' : '#181c1d',
                    }}
                  >
                    {item.label}
                  </Text>
                  {item.value ? (
                    <Text style={{ fontSize: 14, color: '#6e7979' }}>{item.value}</Text>
                  ) : (
                    <MaterialCommunityIcons name="chevron-right" size={20} color="#bdc9c8" />
                  )}
                </Pressable>
              ))}
            </View>
          </View>
        ))}

        {/* Logout */}
        <Pressable
          onPress={handleLogout}
          style={({ pressed }) => ({
            height: 56,
            borderRadius: 16,
            borderWidth: 1.5,
            borderColor: '#ba1a1a',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'row',
            gap: 8,
            opacity: pressed ? 0.7 : 1,
            marginBottom: 16,
          })}
        >
          <MaterialCommunityIcons name="logout" size={20} color="#ba1a1a" />
          <Text style={{ fontSize: 16, fontWeight: '600', color: '#ba1a1a' }}>Log Out</Text>
        </Pressable>

        <Text
          style={{
            textAlign: 'center',
            fontSize: 12,
            color: '#6e7979',
            letterSpacing: 0.5,
          }}
        >
          © 2024 TAMAKKAN AI DRIVING ASSISTANT
        </Text>
      </ScrollView>
    </View>
  );
}
