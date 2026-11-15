# Border-AI Responsible Use Policy & Ethics Framework

**Notice:** *This policy outlines mandatory guidelines for deploying and operating the Border-AI Video Intelligence Platform. This document does not constitute formal legal advice. Deploying organizations must independently verify compliance with regional statutory and data protection laws.*

---

## 1. Purpose & Scope of the Platform

The Border-AI platform is engineered as an **operational decision-support system** for authorized security personnel monitoring physical perimeters, access gates, logistics yards, and critical infrastructure facilities. 

Its primary function is to transform passive video streams into real-time, explainable situational awareness (perimeter line crossings, unauthorized vehicle access, and after-hours loitering) to augment human safety operators.

---

## 2. Authorized & Intended Operational Uses

The software may be deployed strictly for authorized, lawful purposes, including:
- **Perimeter Security & Intrusion Detection:** Detecting unauthorized physical breaches across clearly marked boundary lines, virtual tripwires, and buffer zones.
- **Access Control & Watchlist Management:** Verifying authorized commercial and logistics vehicles at access points against legal, pre-approved watchlists (e.g. stolen vehicle databases, authorized delivery fleets).
- **Traffic Safety & Incident Triage:** Identifying wrong-way driving in restricted lanes, vehicle stalling, or hazardous congestion.
- **Forensic Investigation:** Assisting licensed security investigators in reconstructing vehicle timelines using authorized audit-logged queries.

---

## 3. Explicitly Prohibited Uses

The Border-AI software must **NEVER** be utilized for the following applications:
1. **Autonomous Enforcement or Kinetic Action:** The platform must **never** be integrated into automated weapon systems, lethal autonomous weapons (LAWS), or autonomous physical enforcement without human-in-the-loop review.
2. **Warrantless Public Mass Surveillance:** Indiscriminate, bulk biometric tracking of individuals in public plazas, transit hubs, or civic demonstrations without lawful judicial authorization or statutory authority.
3. **Discriminatory Profiling:** Utilizing computer vision attributes or classification models to profile, harass, or score individuals based on protected characteristics, including race, gender, ethnicity, religion, disability, or political expression.
4. **Covert Domestic Surveillance:** Covert surveillance or stalkerware applications deployed without proper physical signage, consent notices, or legitimate workplace safety justification.

---

## 4. Privacy-by-Design Technical Safeguards

To prevent abuse and mitigate privacy risks, Border-AI implements hard technical boundaries (ADR 0054):
- **Biometrics Disabled by Default:** Facial recognition and cross-camera person appearance Re-ID are **disabled by default** and designated as consent-gated prototypes. They require explicit configuration activation and verifiable consent reference keys.
- **Zero Biometric Embeddings in Public APIs:** Raw 128-dimensional biometric embeddings are strictly isolated within internal database tables and never returned across REST or WebSocket client endpoints.
- **Cryptographic Auditability:** Every search query, export action, alert acknowledgement, and configuration modification is recorded in an immutable, SHA-256 hash-chained audit log (`api_audit_log`) that cannot be tampered with without invalidating the chain.
- **Automated Data Retention & Ephemeral Buffering:** The platform features an automated data retention service that enforces user-configured maximum retention windows (e.g., 90 days for general events, 180 days for alerts), securely purging expired rows and snapshot JPEGs from disk.

---

## 5. Deployer Legal & Compliance Responsibilities

Every deploying organization or system integrator assumes full legal responsibility for its deployment, including:
1. **Regulatory Compliance:** Ensuring adherence to relevant data protection frameworks (such as the EU General Data Protection Regulation [GDPR], California Consumer Privacy Act [CCPA], and national security video surveillance codes).
2. **Data Protection Impact Assessment (DPIA):** Conducting a formal DPIA or risk assessment prior to commissioning live camera feeds.
3. **Transparency & Signage:** Installing clear, prominent physical signage notifying visitors, employees, or motorists that video analytics and license plate recognition are active on the premises.
4. **Operator Training:** Ensuring operators are trained in ethical decision-making, bias mitigation, and data privacy protocols.
