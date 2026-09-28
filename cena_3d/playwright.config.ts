import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://127.0.0.1:5174',
    viewport: { width: 1440, height: 1000 },
    launchOptions: { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
  },
  webServer: [{
    command: 'npm run dev -- --port 5174 --strictPort',
    url: 'http://127.0.0.1:5174',
    reuseExistingServer: false,
    env: { VITE_WS_URL: 'ws://127.0.0.1:8001/ws' },
  }, {
    command: '../.venv/bin/python -m uvicorn motor_python.main:app --app-dir .. --host 127.0.0.1 --port 8001 --workers 1',
    url: 'http://127.0.0.1:8001/docs',
    reuseExistingServer: false,
  }],
});
