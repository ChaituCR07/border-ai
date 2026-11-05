# BorderVision ANPR Camera Placement & Optical Calibration Guide

**Reference Documentation:** ADR 0038, `docs/model_eval/anpr.md`  
**Target:** Field installation engineers and camera system integrators  

---

## 1. The Core Geometric Rule: Plate Height $\ge 30\,\text{Pixels}$

Empirical evaluation across the BorderVision-India-ANPR dataset demonstrates that recognition accuracy correlates directly with the pixel height of the license plate in the captured frame:

- **$\ge 50\,\text{px}$ (Optimal Zone):** $> 95\%$ single-frame exact accuracy.
- **$30 - 50\,\text{px}$ (Operational Zone):** $> 90\%$ exact accuracy; full reliability with multi-frame consensus.
- **$20 - 30\,\text{px}$ (Marginal Zone):** $70 - 85\%$ accuracy; susceptible to optical character confusions (`0` vs `O`, `8` vs `B`).
- **$< 20\,\text{px}$ (Unusable Zone):** $< 50\%$ accuracy; stroke details fall below the optical Nyquist limit.

---

## 2. Lens Focal Length & Distance Calculator

Standard Indian passenger vehicle plates measure $500\,\text{mm} \times 120\,\text{mm}$ (width $\times$ height). Two-wheeler plates measure $200\,\text{mm} \times 100\,\text{mm}$.

To guarantee $H_{\text{plate}} \ge 40\,\text{pixels}$ on a $1080\text{p}$ ($1920\times 1080$) camera:
$$\text{Pixels per Meter (PPM)} = \frac{40\,\text{px}}{0.12\,\text{m}} \approx 333\,\text{PPM}$$

For a sensor width $W_{\text{sensor}}$ (e.g. $1/2.8''$ sensor, $W = 5.6\,\text{mm}$) and vehicle lane distance $D$:
$$f = \frac{D \times \text{PPM} \times W_{\text{sensor}}}{W_{\text{image}}}$$

### Recommended Lens Matrix by Distance

| Capture Distance ($D$) | Sensor Format | Required Focal Length ($f$) | Lens Recommendation |
|---|---|---|---|
| **$4 - 8\,\text{m}$ (Booth Chokepoint)** | $1/2.8''$ CMOS | $4.0 - 8.0\,\text{mm}$ | $2.8 - 12\,\text{mm}$ motorized varifocal |
| **$10 - 18\,\text{m}$ (Entry Approach)** | $1/2.8''$ CMOS | $10.0 - 18.0\,\text{mm}$ | $5 - 50\,\text{mm}$ telephoto varifocal |
| **$20 - 35\,\text{m}$ (Free-Flow Highway)**| $1/2''$ CMOS | $22.0 - 38.0\,\text{mm}$ | $12 - 50\,\text{mm}$ dedicated ANPR lens |

---

## 3. Mounting Angles & Field Geometry

1. **Horizontal Yaw Angle ($\theta_{\text{yaw}} \le 30^\circ$):**
   - Mount camera as close to the lane centerline as structurally permissible.
   - Yaw angles $>30^\circ$ cause severe character foreshortening and intra-character occlusion.
2. **Vertical Pitch Angle ($\theta_{\text{pitch}} \le 25^\circ$):**
   - Optimal mounting pole height: $3.5\,\text{m} - 5.5\,\text{m}$ at $12\,\text{m}$ standoff distance.
   - Steep angles ($>35^\circ$) cause vertical perspective compression and keystoning.

---

## 4. Shutter Speed & Lighting Control

- **Shutter Speed:**
  - Standard CCTV defaults ($1/30\,\text{s}$ or $1/50\,\text{s}$) produce unacceptable motion blur for moving vehicles.
  - Set shutter speed to **$1/1000\,\text{s}$** (minimum $1/500\,\text{s}$ for slow checkpoint crawling lanes).
- **Illumination & Retroreflection:**
  - Deploy synchronized $850\,\text{nm}$ pulsed infrared (IR) illuminators.
  - Active IR overcomes direct vehicle headlight glare and illuminates retroreflective Indian HSRP plates without causing driver distraction.
- **Lens Maintenance:**
  - Apply hydrophobic coating to outer camera domes to prevent droplet accumulation during monsoon seasons.
