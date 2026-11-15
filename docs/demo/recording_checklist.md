# Final Video Recording Pre-Flight Checklist

This checklist must be completely satisfied prior to recording the final demonstration video for the Border-AI Video Intelligence Platform (v1.0.0).

---

## 1. System & Environment Readiness
- [x] Full stack running via `make quickstart` or `make demo`.
- [x] All 10 services report `(healthy)` in `docker compose ps`.
- [x] Synthetic camera simulation feeds actively streaming over RTSP via `mediamtx`.
- [x] Mailpit web interface reachable at `http://localhost:8025` for transactional email inspection.
- [x] Database seeded with demo watchlist vehicles (`KA01AB1234`) and standard camera topology.

---

## 2. Browser & Display Setup
- [x] Browser window resized to exact **1920×1080** viewport at 100% zoom.
- [x] Dark mode enabled across all interfaces.
- [x] Browser bookmarks, developer tools, extensions, and address bar autocompletion hidden.
- [x] System OS notifications, chat messengers, and background chimes disabled (Do Not Disturb).
- [x] Audio: "Enable alert sounds" permission granted on dashboard.
- [x] Second browser window opened in private/incognito mode for cross-session acknowledgement demonstration.

---

## 3. Audio & Narration Hygiene
- [x] Quiet recording room with acoustic treatment / pop filter.
- [x] Microphone levels calibrated with peaks around $-6\,\text{dB}$ and zero audio clipping.
- [x] Speech delivery paced at approximately 130 words per minute according to `storyboard.md`.
- [x] On-screen disclosure caption present: *"Recorded & simulated footage · Synthetic plates · Decision support for authorized operators."*
