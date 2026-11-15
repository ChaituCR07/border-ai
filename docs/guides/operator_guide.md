# Border-AI Operator User Guide

This guide details day-to-day operations for frontline security operators using the Border-AI Command Center dashboard.

---

## 1. Live Monitoring & Dashboard Layout

Upon logging into the web dashboard (`https://localhost`), operators are presented with the **Command Center**:
- **Multi-Camera Grid (2×2):** Displays real-time, low-latency MJPEG feeds from active CCTV cameras. Each camera tile includes an operational status dot (Green = Normal, Yellow = Warning, Red = Offline) and live target bounding boxes.
- **Visual Target Indicators:**
  - **Green / Cyan Box:** Normal detected track (authorized vehicle, pedestrian on sidewalk).
  - **Yellow Box (Score 30–49):** Medium threat (loitering in buffer zone).
  - **Orange / Red Box (Score 50–69):** High threat (restricted zone entry or directional tripwire crossing).
  - **Pulsing Red Box + Red Banner (Score 70–100):** Critical threat (watchlisted stolen vehicle or multi-violation breach).

---

## 2. Real-Time Alert Triage Workflow

When a high or critical threat occurs:
1. **Instant Audio & Visual Notification:** The dashboard plays an alert chime and displays a priority notification toast in the top-right corner.
2. **Reviewing the Alert Drawer:**
   - Click `[VIEW]` on the alert toast or select the incident card from the live alerts stream.
   - The alert drawer opens, displaying the **pre-annotation evidence snapshot** captured at the exact moment of breach.
   - Review the **Explainable Factor Checklist**:
     - `[✓] Restricted Zone Entry (+30 pts)`
     - `[✓] Virtual Line Crossing (+20 pts)`
     - `[✓] After-Hours Movement (+10 pts)`
     - **Calculated Threat Score:** `60 / 100` (`HIGH`)
3. **Acknowledging the Incident (ADR 0016):**
   - Click `[ACKNOWLEDGE]`.
   - Optionally enter an operational note (e.g. *"Patrol dispatched to North Gate"*).
   - Once clicked, the acknowledgement is committed atomically to the database. All other operator screens immediately update to show the alert as acknowledged, silencing the audio alarm.
4. **Resolution:**
   - Once security personnel secure the area, click `[RESOLVE]` to close the incident lifecycle.
