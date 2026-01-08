# BeSTiale Esplo ⛺

**Sistema di Gestione e Coordinamento Campo Scout**

## 🎯 Obiettivo
Una piattaforma centralizzata per monitorare l'andamento del campo, visualizzare il successo delle pattuglie e coordinare l'uso degli spazi logistici.

---

## 🚀 Funzionalità Principali

### 1. Classifica Pattuglie (Leaderboard)
- Visualizzazione in tempo reale dei punteggi di tutte le pattuglie.
- Suddivisione per Sottocampi (Alpino, Montano, Prealpino, Collinare).
- Trasparenza totale sui progressi delle attività.

### 2. Calendario Terreni & Mappatura
- **Mappa Interattiva**: Visualizzazione dei poligoni estratti da KML/KMZ per identificare chiaramente i confini dei terreni.
- **Timeline di Disponibilità**: Stato di occupazione (Libero, Parziale, Occupato) filtrabile per orario e data.
- **Consultazione**: Gli utenti possono vedere dove si trovano le attività e quali terreni sono assegnati, evitando sovrapposizioni logistiche.

### 3. Timeline Attività
- Feed live di tutte le sfide completate.
- Cronologia storica delle imprese portate a termine dalle pattuglie.

---

## 🔒 Accessi e Sicurezza
La piattaforma è progettata come uno strumento di **consultazione**, non di prenotazione self-service.

*   **Amministratori & Gestori (Logistica)**:
    - Unici utenti con permessi di **scrittura**.
    - Inserimento punti e completamento sfide.
    - Gestione e assegnazione dei terreni.
*   **Unità & Utenti Standard**:
    - Permessi di **sola lettura**.
    - Possono consultare la classifica, la disponibilità dei terreni e la timeline.
    - Non possono effettuare prenotazioni o modificare punteggi.

---

## 🛠️ Note Tecniche per la Presentazione
- **Data-Driven**: Tutti i dati (terreni, sfide, unità) sono gestiti tramite semplici file CSV per massima flessibilità.
- **Geolocalizzazione**: Integrazione con Leaflet e poligoni reali per una precisione millimetrica sul campo.
- **Cloud-Ready**: Già configurata per il deployment su Fly.io con persistenza dei dati.
