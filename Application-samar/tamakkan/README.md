# Tamakkan — AI Driving Safety App

React Native + Expo app for the Tamakkan AI driving safety assessment platform.

## Prerequisites

- Node.js 18+ — https://nodejs.org
- Expo CLI: `npm install -g expo-cli`
- Android Studio (for Android emulator) or Expo Go app on your phone

## Setup

```bash
cd Application-samar/tamakkan

# Install dependencies
npm install

# Start development server
npm start

# Run on Android
npm run android

# Run on iOS (Mac only)
npm run ios
```

## Stack

| Layer | Library |
|-------|---------|
| Framework | Expo SDK 52 + Expo Router v4 |
| Language | TypeScript |
| Styling | NativeWind v4 (Tailwind CSS) |
| State | Zustand v5 |
| HTTP | Axios |
| Icons | @expo/vector-icons (MaterialCommunityIcons) |
| Gradients | expo-linear-gradient |
| SVG | react-native-svg |

## Project Structure

```
src/
├── app/
│   ├── (auth)/         # Splash, UserType, Login, Signup
│   ├── (tabs)/         # Home, Progress, Devices, Profile
│   └── session/        # Live driving session
├── components/
│   ├── ui/             # Button, Input, Card, Badge, TopBar
│   └── features/       # ScoreRing, SessionCard, StatCard, TipCard
├── services/api.ts     # Axios + mock data fallback
├── stores/             # authStore, sessionStore (Zustand)
├── theme/index.ts      # Design tokens
├── types/index.ts      # TypeScript interfaces
└── utils/index.ts      # Formatters, validators
```

## Backend

The app connects to a FastAPI server on the Jetson Orin NX edge device.
Configure the IP in `src/services/api.ts`:

```ts
export const API_BASE_URL = 'http://192.168.43.1:8000'; // change to Jetson IP
```

All API calls fall back to mock data when the backend is unreachable, so the
app is fully navigable for demos without a live connection.

## Screens

| Screen | Route |
|--------|-------|
| Splash | `/(auth)/` |
| User Type | `/(auth)/user-type` |
| Login | `/(auth)/login` |
| Sign Up | `/(auth)/signup` |
| Home (Dashboard) | `/(tabs)/` |
| Progress | `/(tabs)/progress` |
| Devices (DashCam) | `/(tabs)/devices` |
| Profile | `/(tabs)/profile` |
| Live Session | `/session/live` |

## Design

Colors, typography, spacing and component patterns follow the Tamakkan design
system defined in `DESIGN.md`. Primary accent is `#008080` (teal), Work Sans
typeface throughout.
