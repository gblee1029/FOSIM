import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// build_exe.ps1이 VERSION.txt와 같은 순간을 넘겨준다. 없으면(개발 서버, 수동 빌드)
// 설정을 읽는 시각을 쓴다.
const buildIso = process.env.FOSIM_BUILD_ISO ?? new Date().toISOString();

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_BUILD_ISO__: JSON.stringify(buildIso),
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
