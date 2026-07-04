import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'tech.universalmetaharness.cockpit',
  appName: 'UMH Cockpit',
  webDir: 'dist-web',
  server: {
    url: 'https://universalmetaharness.tech',
    cleartext: true,
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#07080a',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#07080a',
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
  },
  ios: {
    scheme: 'UMH Cockpit',
    contentInset: 'always',
  },
  android: {
    backgroundColor: '#07080a',
  },
}

export default config
