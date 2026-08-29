# LYC Society frontend

Phase 6A provides the React/Vite/TypeScript Mini App shell. Install with `npm install`, run with `npm run dev`, and build with `npm run build`. Vite proxies `/api` to `http://127.0.0.1:8000`; set `VITE_API_BASE_URL` only to a public browser-safe path. Telegram authentication uses `GET /api/v1/auth/csrf/`, then `POST /api/v1/auth/telegram/` with Telegram's raw `initData` and cookie credentials. No bot token or server secret belongs in frontend environment variables.
