# Terrain Reservation & GIS System

## 🗺️ Geospatial Foundation
The application manages physical camp spaces ("Terreni") using geographic coordinates.

### KML Integration
- Terrains are typically imported from KML/KMZ files (standard Google Earth format).
- `kml_to_terreni.py`: A specialized script that parses KML files, extracts polygons, and calculates the centroid (`center_lat`, `center_lon`) for map centering.
- The polygons are stored in the database as **JSON stringified lists of coordinates**.

---

## 📅 Reservation Engine
The system allows units to book specific time slots for these terrains.

### Configuration & Restrictions
- **Slots**: Reservations are made for durations between 1 and 4 hours.
- **Time Window**: Allowed hours are usually between 07:00 and 01:00 (next day).
- **Access Control**: Terrains can be restricted to specific group types (`tipo_accesso`: "reparto", "posto", or "entrambi").

### Status Lifecycle
1. **PENDING**: Initial state upon submission by a Unit.
2. **APPROVED**: Set by Staff/Admin.
3. **REJECTED**: Manually set or automatically triggered by conflict resolution.
4. **CANCELLED**: Set by the Unit before approval.

### 🛡️ Conflict Resolution Logic
When a Staff member **approves** a reservation:
- The system automatically identifies all other **PENDING** reservations that overlap with the same terrain and time window.
- These overlapping requests are automatically marked as **REJECTED** to maintain schedule integrity.

---

## 🗺️ Interactive Map (Frontend)
- **Leaflet Integration**: Renders polygons directly on the client side.
- **Real-time Availability**:
    - **Green**: Fully available for the selected slot.
    - **Yellow**: Partially booked (other reservations exist in the same period).
    - **Grey**: Fully booked.
- **Data Fetching**: The frontend queries `/api/terreni/availability` with a date range, and the backend calculates overlap percentages to return the correct status.
