import React from 'react';
import { View, Text, ViewStyle } from 'react-native';

type BadgeVariant = 'primary' | 'secondary' | 'tertiary' | 'error' | 'outline';

const variantStyles: Record<BadgeVariant, { bg: string; text: string }> = {
  primary: { bg: 'rgba(0,128,128,0.12)', text: '#006565' },
  secondary: { bg: 'rgba(128,249,202,0.3)', text: '#007354' },
  tertiary: { bg: 'rgba(255,222,168,0.3)', text: '#5e4200' },
  error: { bg: 'rgba(186,26,26,0.1)', text: '#ba1a1a' },
  outline: { bg: 'transparent', text: '#6e7979' },
};

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  style?: ViewStyle;
}

export function Badge({ label, variant = 'primary', style }: BadgeProps) {
  const s = variantStyles[variant];
  return (
    <View
      style={[
        {
          backgroundColor: s.bg,
          paddingHorizontal: 10,
          paddingVertical: 4,
          borderRadius: 9999,
          alignSelf: 'flex-start',
        },
        style,
      ]}
    >
      <Text
        style={{
          fontSize: 12,
          fontWeight: '600',
          letterSpacing: 0.5,
          color: s.text,
          textTransform: 'uppercase',
        }}
      >
        {label}
      </Text>
    </View>
  );
}
