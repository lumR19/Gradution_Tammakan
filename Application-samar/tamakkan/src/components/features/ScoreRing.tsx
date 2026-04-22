import React from 'react';
import { View, Text } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface ScoreRingProps {
  score: number;
  maxScore: number;
  size?: number;
  strokeWidth?: number;
  showIcon?: boolean;
}

export function ScoreRing({
  score,
  maxScore,
  size = 96,
  strokeWidth = 8,
  showIcon = true,
}: ScoreRingProps) {
  const r = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const progress = score / maxScore;
  const offset = circumference * (1 - progress);

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg
        width={size}
        height={size}
        style={{ position: 'absolute', transform: [{ rotate: '-90deg' }] }}
      >
        <Circle
          cx={cx}
          cy={cy}
          r={r}
          stroke="#e6e9e9"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        <Circle
          cx={cx}
          cy={cy}
          r={r}
          stroke="#006565"
          strokeWidth={strokeWidth}
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </Svg>
      {showIcon && (
        <MaterialCommunityIcons name="star-circle" size={32} color="#006565" />
      )}
    </View>
  );
}
