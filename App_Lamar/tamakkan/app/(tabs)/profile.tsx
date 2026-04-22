import { View, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';

export default function ProfileScreen() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.background }}>
      <View
        style={{
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          gap: 8,
        }}
      >
        <Text style={{ fontSize: 24, fontWeight: '700', color: Colors.surface.on }}>
          Profile
        </Text>
        <Text style={{ fontSize: 14, color: Colors.outline.DEFAULT }}>
          Profile screen — future batch
        </Text>
      </View>
    </SafeAreaView>
  );
}
