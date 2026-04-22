import React from 'react';
import { View, Text, Pressable, ScrollView } from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { TopBar } from '../../components/ui/TopBar';
import { useAuthStore } from '../../stores/authStore';
import type { UserType } from '../../types';

const USER_TYPES: {
  type: UserType;
  label: string;
  description: string;
  icon: keyof typeof MaterialCommunityIcons.glyphMap;
  iconBg: string;
  iconColor: string;
  available: boolean;
}[] = [
  {
    type: 'individual',
    label: 'Individual',
    description: 'Review your personal driving performance and safety metrics.',
    icon: 'account',
    iconBg: 'rgba(0,128,128,0.1)',
    iconColor: '#008080',
    available: true,
  },
  {
    type: 'trainee',
    label: 'Trainee',
    description: 'Access learning modules and track your progress through driving courses.',
    icon: 'school',
    iconBg: 'rgba(128,249,202,0.3)',
    iconColor: '#006c4f',
    available: false,
  },
  {
    type: 'instructor',
    label: 'Instructor',
    description: 'Manage students, evaluate sessions, and monitor fleet performance.',
    icon: 'account-supervisor',
    iconBg: 'rgba(255,222,168,0.5)',
    iconColor: '#5e4200',
    available: false,
  },
];

export default function UserTypeScreen() {
  const setUserType = useAuthStore((s) => s.setUserType);

  function handleSelect(type: UserType) {
    setUserType(type);
    router.push('/(auth)/login');
  }

  return (
    <View style={{ flex: 1, backgroundColor: '#f7fafa' }}>
      <TopBar showBack={false} showContact />

      <ScrollView
        contentContainerStyle={{
          flexGrow: 1,
          alignItems: 'center',
          justifyContent: 'center',
          paddingHorizontal: 24,
          paddingVertical: 32,
        }}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={{ alignItems: 'center', marginBottom: 32, maxWidth: 360 }}>
          <Text style={{ fontSize: 28, fontWeight: '700', color: '#181c1d', textAlign: 'center' }}>
            Choose User Type
          </Text>
          <Text
            style={{
              fontSize: 16,
              color: '#3e4949',
              textAlign: 'center',
              marginTop: 8,
              lineHeight: 24,
            }}
          >
            Select the profile that best describes your role in the Tamakkan driving ecosystem.
          </Text>
        </View>

        {/* Cards */}
        <View style={{ width: '100%', maxWidth: 480, gap: 12 }}>
          {USER_TYPES.map((item) => (
            <Pressable
              key={item.type}
              onPress={() => item.available && handleSelect(item.type)}
              style={({ pressed }) => ({
                backgroundColor: '#ffffff',
                borderRadius: 24,
                padding: 24,
                flexDirection: 'row',
                alignItems: 'center',
                borderWidth: 2,
                borderColor: pressed && item.available ? '#008080' : 'transparent',
                shadowColor: '#008080',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.06,
                shadowRadius: 12,
                elevation: 3,
                opacity: item.available ? (pressed ? 0.92 : 1) : 0.5,
                transform: [{ scale: pressed && item.available ? 0.98 : 1 }],
              })}
            >
              <View
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 16,
                  backgroundColor: item.iconBg,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <MaterialCommunityIcons name={item.icon} size={32} color={item.iconColor} />
              </View>

              <View style={{ flex: 1, marginLeft: 16 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <Text style={{ fontSize: 18, fontWeight: '600', color: '#181c1d' }}>
                    {item.label}
                  </Text>
                  {!item.available && (
                    <View
                      style={{
                        backgroundColor: '#ebeeee',
                        paddingHorizontal: 8,
                        paddingVertical: 2,
                        borderRadius: 999,
                      }}
                    >
                      <Text style={{ fontSize: 10, fontWeight: '600', color: '#6e7979' }}>
                        COMING SOON
                      </Text>
                    </View>
                  )}
                </View>
                <Text style={{ fontSize: 14, color: '#3e4949', marginTop: 4, lineHeight: 20 }}>
                  {item.description}
                </Text>
              </View>

              <MaterialCommunityIcons name="chevron-right" size={24} color="#6e7979" />
            </Pressable>
          ))}
        </View>

        {/* Page indicator dots */}
        <View style={{ flexDirection: 'row', gap: 8, marginTop: 32 }}>
          <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: '#008080' }} />
          <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: '#bdc9c8' }} />
          <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: '#bdc9c8' }} />
        </View>
      </ScrollView>
    </View>
  );
}
