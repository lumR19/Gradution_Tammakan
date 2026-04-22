import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Colors from '@/theme/colors';

export default function ProgressScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.logoRow}>
          <View style={styles.logoMini}>
            <MaterialCommunityIcons name="chip" size={18} color="#fff" />
          </View>
          <Text style={styles.logoText}>Tamakkan</Text>
        </View>
        <Text style={styles.langToggle}>EN</Text>
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
    paddingHorizontal: 20,
    height: 60,
    backgroundColor: '#fff',
    shadowColor: Colors.primary.tint,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 20,
    elevation: 3,
  },
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  logoMini: {
    width: 30,
    height: 30,
    borderRadius: 8,
    backgroundColor: Colors.primary.DEFAULT,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: {
    fontSize: 15,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
  },
  langToggle: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.primary.DEFAULT,
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
});
