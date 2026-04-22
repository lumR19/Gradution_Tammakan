import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, TextInputProps } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface InputProps extends TextInputProps {
  label: string;
  iconName?: keyof typeof MaterialCommunityIcons.glyphMap;
  error?: string;
  secure?: boolean;
}

export function Input({ label, iconName, error, secure = false, ...rest }: InputProps) {
  const [visible, setVisible] = useState(!secure);

  return (
    <View style={{ gap: 6 }}>
      <Text
        style={{
          fontSize: 12,
          fontWeight: '600',
          letterSpacing: 0.5,
          color: '#006565',
          marginLeft: 4,
          textTransform: 'uppercase',
        }}
      >
        {label}
      </Text>
      <View style={{ position: 'relative' }}>
        {iconName && (
          <View
            style={{
              position: 'absolute',
              left: 16,
              top: 0,
              bottom: 0,
              justifyContent: 'center',
              zIndex: 1,
            }}
          >
            <MaterialCommunityIcons name={iconName} size={20} color="#6e7979" />
          </View>
        )}
        <TextInput
          secureTextEntry={secure && !visible}
          style={{
            height: 56,
            backgroundColor: '#E9EFEF',
            borderRadius: 16,
            paddingLeft: iconName ? 48 : 16,
            paddingRight: secure ? 48 : 16,
            fontSize: 16,
            color: '#181c1d',
          }}
          placeholderTextColor="#bdc9c8"
          {...rest}
        />
        {secure && (
          <Pressable
            onPress={() => setVisible((v) => !v)}
            style={{
              position: 'absolute',
              right: 16,
              top: 0,
              bottom: 0,
              justifyContent: 'center',
            }}
          >
            <MaterialCommunityIcons
              name={visible ? 'eye-off' : 'eye'}
              size={20}
              color="#6e7979"
            />
          </Pressable>
        )}
      </View>
      {error ? (
        <Text style={{ fontSize: 12, color: '#ba1a1a', marginLeft: 4 }}>{error}</Text>
      ) : null}
    </View>
  );
}
