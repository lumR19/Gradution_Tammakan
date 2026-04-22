import React from 'react';
import { View, Text } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import type { DrivingTip } from '../../types';

interface TipCardProps {
  tip: DrivingTip;
}

export function TipCard({ tip }: TipCardProps) {
  return (
    <View
      style={{
        backgroundColor: '#008080',
        borderRadius: 24,
        padding: 24,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <View style={{ position: 'relative', zIndex: 1 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <MaterialCommunityIcons name="lightbulb" size={20} color="#e3fffe" />
          <Text
            style={{
              fontSize: 12,
              fontWeight: '600',
              letterSpacing: 0.5,
              color: '#e3fffe',
              textTransform: 'uppercase',
            }}
          >
            DAILY DRIVING TIP
          </Text>
        </View>
        <Text style={{ fontSize: 16, fontWeight: '500', color: '#e3fffe', lineHeight: 24 }}>
          {tip.text}
        </Text>
      </View>
      {/* Decorative circle */}
      <View
        style={{
          position: 'absolute',
          right: -32,
          bottom: -32,
          width: 128,
          height: 128,
          borderRadius: 64,
          backgroundColor: 'rgba(255,255,255,0.08)',
        }}
      />
    </View>
  );
}
