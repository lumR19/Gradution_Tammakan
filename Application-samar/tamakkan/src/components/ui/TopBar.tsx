import React from 'react';
import { View, Image, Pressable, Text } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

const LOGO_URI =
  'https://lh3.googleusercontent.com/aida/ADBb0uhCH7ghb4fmdcnQlGm2NMUCj9hJ-rtJDFWgAKafPnD4pRwz1xXWZ4G3vhTWO5w9d5M762zv08HTX_QLjz4RnN4urovLeuHaLb7LUyrKSYdzOPb8Ss78kSQYhW3CnYTXXmjqBaXmXMeT9MFiAKv7NTLfmsJO3Sxq_SQHzNCSPEyCLbVUCTlwsyNCv50xb57Jz-blkLhPBOQTRw3sNbxvIyampS2w8f9Ka_BbozRq6QWUtPr3BvF8nDmX9PpgrpWfw5Ko3n7npThTWw';

interface TopBarProps {
  showBack?: boolean;
  showContact?: boolean;
  right?: React.ReactNode;
}

export function TopBar({ showBack = true, showContact = false, right }: TopBarProps) {
  const insets = useSafeAreaInsets();

  return (
    <View
      style={{
        backgroundColor: '#ffffff',
        paddingTop: insets.top,
        paddingHorizontal: 24,
        height: 64 + insets.top,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        shadowColor: '#008080',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.06,
        shadowRadius: 12,
        elevation: 4,
        zIndex: 50,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        {showBack && (
          <Pressable
            onPress={() => router.back()}
            style={({ pressed }) => ({
              padding: 8,
              borderRadius: 999,
              backgroundColor: pressed ? 'rgba(0,128,128,0.08)' : 'transparent',
            })}
          >
            <MaterialCommunityIcons name="arrow-left" size={24} color="#008080" />
          </Pressable>
        )}
        <Image source={{ uri: LOGO_URI }} style={{ width: 120, height: 40 }} resizeMode="contain" />
      </View>

      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
        {showContact && (
          <Pressable
            style={({ pressed }) => ({
              flexDirection: 'row',
              alignItems: 'center',
              gap: 4,
              paddingHorizontal: 12,
              paddingVertical: 8,
              borderRadius: 8,
              backgroundColor: pressed ? 'rgba(0,128,128,0.08)' : 'transparent',
            })}
          >
            <MaterialCommunityIcons name="face-agent" size={20} color="#008080" />
            <Text style={{ fontSize: 12, fontWeight: '600', letterSpacing: 0.5, color: '#008080' }}>
              CONTACT US
            </Text>
          </Pressable>
        )}
        {right ?? (
          <Text style={{ fontSize: 16, fontWeight: '700', color: '#008080' }}>EN</Text>
        )}
      </View>
    </View>
  );
}
