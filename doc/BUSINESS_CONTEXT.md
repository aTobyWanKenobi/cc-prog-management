# Business & Organizational Context

## 🌳 The Scout Camp Environment
BeSTiapp is designed to serve a large-scale **Scout Camp**, likely involving hundreds of participants organized into different age groups and sub-camps.

---

## 🏛️ Organizational Structure
The app mirrors the scout hierarchy:
- **Unità (Units)**: The primary groups (e.g., Scout Groups from different cities).
    - **Reparto (Scouts)**: Age 12-16. Highly competitive, organized into *Pattuglie*.
    - **Posto (Rovers/Pioneers)**: Age 16-21. Focused on service and logistics; they use the reservation system but don't compete in the ranking.
- **Pattuglia (Patrol)**: Small teams of 6-8 scouts within a *Reparto*. They are the "end-users" of the scoring system.
- **Sottocampo (Sub-camp)**: Large geographic divisions of the main camp (Alpino, Prealpino, etc.). Each unit is assigned to one.
- **Staff/Direzione**: The organizers (Scout Leaders) who manage the camp's logistics and "referee" the activities.

---

## 🎯 Business Needs & "Pain Points"
Before BeSTiapp, these processes were likely manual (paper-based), leading to:
- **Resource Conflict**: Two groups showing up to the same sports field at the same time.
- **Scoring Delays**: Patrols not knowing their rank until the end of the camp.
- **Communication Gaps**: Difficulty in tracking which challenges were completed by whom.

---

## 🛠️ System Purpose
BeSTiapp is **not** a social media platform; it is a **Mission-Critical Operational Tool** for the camp duration.
- **Point Entry**: Must be fast and reliable for staff "in the field."
- **Map View**: Must be mobile-friendly for units navigating the camp area to find their reserved terrain.
- **Timeline**: Acts as a "Live Feed" of the camp's progress to maintain high morale and engagement.

---

## 🏭 Operational Model
The system is built for **short-term, high-intensity use**.
- Data is seeded at the start of the week (`init_db.py`).
- Intense activity occurs daily.
- Data is exported at the end for the final awards ceremony.
- The system might be "reset" and reused for a different camp session later.
