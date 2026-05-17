import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';
import AppLogo from '@/components/AppLogo';

export default function ProgressScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <AppLogo size="mini" />
        <TouchableOpacity onPress={() => router.push('/(tabs)/profile')} hitSlop={12} style={styles.profileBtn}>
          <MaterialCommunityIcons name="account" size={22} color={Colors.primary.container} />
        </TouchableOpacity>
      </View>

      {/* Coming soon body */}
      <View style={styles.body}>
        <View style={styles.iconWrap}>
          <MaterialCommunityIcons
            name="chart-line"
            size={56}
            color={Colors.primary.container}
          />
        </View>
        <Text style={styles.title}>Progress</Text>
        <Text style={styles.subtitle}>
          Detailed charts and session history are coming in the next update.
        </Text>
        <View style={styles.pill}>
          <MaterialCommunityIcons name="clock-outline" size={14} color={Colors.primary.DEFAULT} />
          <Text style={styles.pillText}>Coming Soon</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingLeft: 1,
    paddingRight: 16,
    height: 60,
    backgroundColor: '#fff',
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  body: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 40,
    gap: 16,
  },
  iconWrap: {
    width: 104,
    height: 104,
    borderRadius: 52,
    backgroundColor: `${Colors.primary.container}18`,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: Colors.surface.on,
  },
  subtitle: {
    fontSize: 15,
    color: Colors.outline.DEFAULT,
    textAlign: 'center',
    lineHeight: 22,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 7,
    backgroundColor: `${Colors.primary.fixed}55`,
    borderRadius: 999,
    marginTop: 4,
  },
  pillText: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.primary.DEFAULT,
  },
  profileBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: `${Colors.primary.container}22`,
    borderWidth: 2,
    borderColor: Colors.primary.container,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
