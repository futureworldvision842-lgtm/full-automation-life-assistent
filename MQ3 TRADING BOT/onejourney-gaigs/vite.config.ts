import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 4173 },
  test: {
    environment: 'node',
    include: ['src/tests/**/*.test.ts']
  }
});
