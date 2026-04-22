import React from 'react';
import { View, Text } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import Colors from '@/theme/colors';

interface ScoreRingProps {
  score: number;
  maxScore?: number;
  size?: number;
  strokeWidth?: number;
  showCenter?: boolean;
  centerIcon?: React.ReactNode;
}

export default function ScoreRing({
  score,
  maxScore = 100,
  size = 80,
  strokeWidth = 8,
  showCenter = false,
  centerIcon,
}: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(score / maxScore, 0), 1);
  const strokeDashoffset = circumference * (1 - progress);
  const center = size / 2;

  const color =
    progress >= 0.9
      ? Colors.score.excellent
      : progress >= 0.75
      ? Colors.score.good
      : progress >= 0.6
      ? Colors.score.improving
      : Colors.score.poor;

  return (
    <View
      style={{
        width: size,
        height: size,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Svg
        width={size}
        height={size}
        style={{ position: 'absolute' }}
      >
        {/* Track ring */}
        <Circle
          cx={center}
          cy={center}
          r={radius}
          stroke={Colors.surface.containerHighest}
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress ring */}
        <Circle
          cx={center}
          cy={center}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          rotation="-90"
          origin={`${center}, ${center}`}
        />
      </Svg>

      {centerIcon ?? (showCenter && (
        <Text
          style={{
            fontSize: maxScore === 5 ? 14 : 16,
            fontWeight: '700',
            color,
          }}
        >
          {maxScore === 5 ? score.toFixed(1) : Math.round(score).toString()}
        </Text>
      ))}
    </View>
  );
}
