# 46. Alert-Fatigue Targets and False-Positive Reporting Policy

Date: 2026-11-12
Status: Accepted

## Context

Surveillance platforms frequently lose credibility with operators when false alarms exceed human cognitive capacity. In a security operations center (SOC), an operator handling 10 camera feeds can realistically review at most 3 to 5 critical alerts per hour without alert fatigue. Furthermore, marketing claims often cite misleading metrics such as "0.01% false alarm rate" without defining the denominator (frames? detections? hours?).

A defensible standard requires fixed operational alert-fatigue targets agreed upon before testing, paired with strict reporting rules enforced by automated claims linting.

## Decisions

### 1. Alert-Fatigue Design Targets

The platform is evaluated against the following quantitative criteria on the frozen production configuration:

| Metric Category | Target Specification | Enforcement Mechanism |
|---|---|---|
| **Controlled Test Pairs (Plan 1-6)** | 100% pass on core variants; $\ge 90\%$ on boundary stress variants. | Automated system spec runner × 3 runs. |
| **Logic Property Suite** | 100% pass across all property tests and planted mutation checks. | Automated hypothesis property tests in CI. |
| **High Tier False Alerts ($\ge\text{HIGH}$)** | $\le 0.10$ alerts per camera-hour on unique normal footage ($\approx 2.4$ per camera-day). | Poisson 95% interval on held-out exposure partition. |
| **Critical Tier False Alerts ($\text{CRITICAL}$)** | Design target $\le 0.01$ alerts per camera-hour ($\le 1$ per 4 camera-days). | Exact Poisson upper bound reported when 0 events observed. |
| **Rule-Level Precision & Recall vs Oracle** | Precision $\ge 0.90$ with Recall $\ge 0.90$ on static cameras. | Replay matching $\pm 1.0\,\text{s}$ against GT tracks. |
| **Watchlist False Matches** | $\le 1.0$ false matches per 1,000 reads on 100-plate list under deployed policy. | Empirical sampling over held-out reads. |
| **Alert Burstiness** | $\le 3$ alerts per minute per camera during transient perturbations. | Cooldown and rearm collapse verification. |
| **Sensitivity Guard** | $\ge 95\%$ positive incident retention across all mitigations. | Automated guard regression suite. |

### 2. Standardized Reporting Template (README Line)

Every public claim regarding false positives must follow the exact structure below:

```text
False positive rate: <rate> alerts (tier >= HIGH) per camera-hour on <N> camera-hours of unique
normal footage (95% CI [lo, hi]; <sources>; held-out split) [run:<run_id>]. Controlled tests: 6/6 pairs pass
(<m>/<n> variants). Watchlist: <x> false matches per 1,000 reads at watchlist size <w> [run:<run_id>].
```

**Zero-Event Protocol:**  
If zero events are observed ($k = 0$), the statement must never claim "0% false alarms". It must explicitly state the observation and the Poisson one-sided 95% upper bound ($3.689 / N$):
```text
False positive rate: 0 FP alerts (tier >= HIGH) in 4.25 camera-hours of unique normal footage
(95% upper bound 0.868/cam-h; static perimeter & gate scenes; held-out split) [run:exp-20261112-01].
Controlled tests: 6/6 pairs pass (19/19 variants). Watchlist: 0.0 false matches per 1,000 reads
at watchlist size 100 [run:wl-20261112-01].
```

## Consequences

- Automated linting in `scripts/report/check_claims.py` rejects bare percentages (e.g. "FP rate: 0.1%") or uncredited claims lacking exposure hours, confidence intervals, and run IDs.
- Operators receive transparent documentation of known operational limitations (e.g. night IR spider webs, torrential rain glare).
