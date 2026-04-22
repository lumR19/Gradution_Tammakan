import React from 'react';
import { Pressable, Text, ActivityIndicator, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

type Variant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  style?: ViewStyle;
  fullWidth?: boolean;
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
  icon,
  style,
  fullWidth = true,
}: ButtonProps) {
  const isDisabled = disabled || loading;

  if (variant === 'primary') {
    return (
      <Pressable
        onPress={onPress}
        disabled={isDisabled}
        style={({ pressed }) => [
          { opacity: pressed || isDisabled ? 0.75 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] },
          fullWidth && { width: '100%' },
          style,
        ]}
      >
        <LinearGradient
          colors={['#008080', '#006c4f']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={{
            height: 56,
            borderRadius: 16,
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            shadowColor: '#008080',
            shadowOffset: { width: 0, height: 8 },
            shadowOpacity: 0.25,
            shadowRadius: 16,
            elevation: 6,
          }}
        >
          {loading ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <>
              {icon}
              <Text style={{ color: '#ffffff', fontSize: 18, fontWeight: '600' }}>{label}</Text>
            </>
          )}
        </LinearGradient>
      </Pressable>
    );
  }

  if (variant === 'secondary') {
    return (
      <Pressable
        onPress={onPress}
        disabled={isDisabled}
        style={({ pressed }) => [
          {
            height: 56,
            borderRadius: 16,
            borderWidth: 1.5,
            borderColor: '#008080',
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            opacity: pressed || isDisabled ? 0.6 : 1,
          },
          fullWidth && { width: '100%' },
          style,
        ]}
      >
        {icon}
        <Text style={{ color: '#008080', fontSize: 16, fontWeight: '600' }}>{label}</Text>
      </Pressable>
    );
  }

  // ghost
  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        {
          paddingHorizontal: 12,
          paddingVertical: 8,
          borderRadius: 8,
          opacity: pressed ? 0.6 : 1,
        },
        style,
      ]}
    >
      <Text style={{ color: '#006565', fontSize: 12, fontWeight: '600', letterSpacing: 0.5 }}>
        {label}
      </Text>
    </Pressable>
  );
}
