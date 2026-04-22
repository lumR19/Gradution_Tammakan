import React from 'react';
import { View, ViewStyle } from 'react-native';

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  padding?: number;
  radius?: number;
}

export function Card({ children, style, padding = 20, radius = 24 }: CardProps) {
  return (
    <View
      style={[
        {
          backgroundColor: '#ffffff',
          borderRadius: radius,
          padding,
          shadowColor: '#008080',
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.06,
          shadowRadius: 12,
          elevation: 3,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}
