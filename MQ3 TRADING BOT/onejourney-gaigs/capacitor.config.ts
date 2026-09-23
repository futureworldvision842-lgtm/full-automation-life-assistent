import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'org.onejourney.gaigs',
  appName: 'GAIGS / OneJourney',
  webDir: 'dist',
  android: { allowMixedContent: false },
  plugins: {
    Geolocation: {
      permissions: ['location']
    }
  }
};

export default config;
