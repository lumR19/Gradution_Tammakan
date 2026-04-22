export const colors = {
  primary: '#006565',
  primaryContainer: '#008080',
  onPrimary: '#ffffff',
  onPrimaryContainer: '#e3fffe',
  primaryFixed: '#93f2f2',
  inversePrimary: '#76d6d5',
  secondary: '#006c4f',
  secondaryContainer: '#80f9ca',
  onSecondary: '#ffffff',
  onSecondaryContainer: '#007354',
  tertiary: '#775400',
  tertiaryFixed: '#ffdea8',
  onTertiaryFixedVariant: '#5e4200',
  surface: '#f7fafa',
  surfaceContainerLowest: '#ffffff',
  surfaceContainerLow: '#f1f4f4',
  surfaceContainer: '#ebeeee',
  surfaceContainerHigh: '#e6e9e9',
  surfaceContainerHighest: '#e0e3e3',
  onSurface: '#181c1d',
  onSurfaceVariant: '#3e4949',
  outline: '#6e7979',
  outlineVariant: '#bdc9c8',
  background: '#f7fafa',
  onBackground: '#181c1d',
  error: '#ba1a1a',
  errorContainer: '#ffdad6',
  onError: '#ffffff',
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  gutter: 16,
} as const;

export const radius = {
  sm: 4,
  md: 8,
  lg: 16,
  xl: 24,
  full: 9999,
} as const;

export const shadows = {
  card: {
    shadowColor: '#008080',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.06,
    shadowRadius: 12,
    elevation: 3,
  },
  button: {
    shadowColor: '#008080',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.2,
    shadowRadius: 16,
    elevation: 6,
  },
} as const;

export const typography = {
  headlineLg: { fontSize: 28, fontWeight: '700' as const, lineHeight: 36 },
  headlineMd: { fontSize: 22, fontWeight: '600' as const, lineHeight: 28 },
  bodyLg: { fontSize: 16, fontWeight: '400' as const, lineHeight: 24 },
  bodyMd: { fontSize: 14, fontWeight: '400' as const, lineHeight: 20 },
  labelCaps: { fontSize: 12, fontWeight: '600' as const, lineHeight: 16, letterSpacing: 0.5 },
  dataNum: { fontSize: 24, fontWeight: '700' as const, lineHeight: 30 },
} as const;
