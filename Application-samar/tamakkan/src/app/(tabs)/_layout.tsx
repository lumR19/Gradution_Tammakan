import React from 'react';
import { Tabs } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Platform } from 'react-native';

type IconName = keyof typeof MaterialCommunityIcons.glyphMap;

const TAB_ITEMS: { name: string; title: string; icon: IconName; iconFilled: IconName }[] = [
  { name: 'index', title: 'Home', icon: 'home-outline', iconFilled: 'home' },
  { name: 'progress', title: 'Progress', icon: 'chart-bar', iconFilled: 'chart-bar' },
  { name: 'devices', title: 'Devices', icon: 'router-wireless', iconFilled: 'router-wireless' },
  { name: 'profile', title: 'Profile', icon: 'account-outline', iconFilled: 'account' },
];

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: 'rgba(255,255,255,0.95)',
          borderTopColor: '#f1f4f4',
          height: Platform.OS === 'ios' ? 84 : 64,
          paddingBottom: Platform.OS === 'ios' ? 24 : 8,
          paddingTop: 8,
          shadowColor: '#008080',
          shadowOffset: { width: 0, height: -4 },
          shadowOpacity: 0.06,
          shadowRadius: 12,
          elevation: 8,
        },
        tabBarActiveTintColor: '#008080',
        tabBarInactiveTintColor: '#94a3b8',
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '500',
        },
      }}
    >
      {TAB_ITEMS.map((tab) => (
        <Tabs.Screen
          key={tab.name}
          name={tab.name}
          options={{
            title: tab.title,
            tabBarIcon: ({ focused, color, size }) => (
              <MaterialCommunityIcons
                name={focused ? tab.iconFilled : tab.icon}
                size={24}
                color={color}
              />
            ),
          }}
        />
      ))}
    </Tabs>
  );
}
