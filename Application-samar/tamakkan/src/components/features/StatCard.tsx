import React from 'react';
import { View, Text } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  iconName: keyof typeof MaterialCommunityIcons.glyphMap;
  iconBg: string;
  iconColor: string;
  subtitle?: string;
}

export function StatCard({
  label,
  value,
  unit,
  iconName,
  iconBg,
  iconColor,
  subtitle,
}: StatCardProps) {
  return (
    <View
      style={{
        backgroundColor: '#ffffff',
        borderRadius: 24,
        padding: 20,
        flex: 1,
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
          backgroundColor: iconBg,
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 12,
        }}
      >
        <MaterialCommunityIcons name={iconName} size={20} color={iconColor} />
      </View>
      <Text
        style={{
          fontSize: 12,
          fontWeight: '600',
          letterSpacing: 0.5,
          color: '#3e4949',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </Text>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 4, marginTop: 4 }}>
        <Text style={{ fontSize: 28, fontWeight: '700', color: '#181c1d' }}>{value}</Text>
        {unit && (
          <Text style={{ fontSize: 14, color: '#6e7979' }}>{unit}</Text>
        )}
      </View>
      {subtitle && (
        <Text style={{ fontSize: 14, color: '#3e4949', marginTop: 2 }}>{subtitle}</Text>
      )}
    </View>
  );
}
