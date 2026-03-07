# Challenge Ranking & Completion System

## 🏆 Scoring Philosophy
The "Punteggiometro" (Point Meter) is the competitive heart of BeSTiapp. It tracks the progress of various Patrols ("Pattuglie") via a challenge-driven leaderboard.

---

## 🧩 Key Entities
- **Pattuglia**: The competitor. Linked to an **Unita** (Unit/Group).
- **Challenge**: A specific task or achievement with a defined point value.
- **Completion**: A record of a specific Patrol successfully finishing a specific Challenge.

---

## 📈 Ranking Logic
- **Current Score**: Each Patrol has a `current_score` field in the database.
- **Real-time Updates**: When a "Completion" is registered by staff, the Patrol's score is immediately incremented by the Challenge's point value.
- **Leaderboard**: A dynamic view that sorts Patrols by `current_score` descending.
- **Filtering**: Rankings can be filtered by:
    - **Sottocampo**: Sub-camp areas (e.g., Alpino, Montano).
    - **Tipo**: Unit type (Reparto/Posto).

---

## 🛠️ Management & Integrity
### Point Entry
Only **Staff (Tech)** or **Admin** users can register completions. They use an `/input` page to select the Patrol and the Challenge. The system prevents duplicate completions for the same Patrol + Challenge combination.

### 🍄 Special Challenges ("Fungo")
Challenges marked as `is_fungo` are special/bonus tasks. They might also provide `reward_tokens`, an secondary currency used for internal camp "shop" or reward mechanics.

### Retroactive Corrections
The Admin interface allows for sophisticated corrections:
- **Rollback**: Deleting a completion record automatically deducts the associated points from the Patrol.
- **Point Adjustment**: If a Challenge's point value is changed, the Admin can choose to **retroactively update** all existing Patrol scores based on previously recorded completions of that challenge.

### 🕒 Timeline Feed
A public "Timeline" route shows a live feed of the most recent 100 completions, fostering a sense of active competition across the camp.
