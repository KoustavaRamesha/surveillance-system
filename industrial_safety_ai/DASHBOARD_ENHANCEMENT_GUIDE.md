# Dashboard Enhancement Guide

This guide explains how to integrate the new **EnhancedAlertPanel** into the existing desktop application for better alert visualization and user experience.

## What's New

### EnhancedAlertPanel Features
- **Severity-based color coding**: Red (Critical), Orange (High), Amber (Medium), Green (Low)
- **Emoji icons**: Quick visual identification (🚨 ⚠️ ⚡ ℹ️)
- **Confidence visualization**: Progress bar showing detection confidence (0-100%)
- **Action recommendations**: Clear, actionable guidance for each incident
- **Live status tracking**: Open → Acknowledged → Resolved workflow
- **Animated entry**: Smooth slide-in animation when alerts appear
- **Summary statistics**: Real-time counts of Open/Acknowledged/Resolved incidents
- **Human-readable messages**: Event types formatted as titles (e.g., `restricted_area_intrusion` → "Restricted Area Intrusion")

## Integration Steps

### Step 1: Replace the AlertPanel import in `main_window.py`

**Old:**
```python
from ui.alert_panel import AlertPanel
```

**New:**
```python
from ui.enhanced_alert_panel import EnhancedAlertPanel as AlertPanel
```

### Step 2: Update the AlertPanel instantiation

In `MainWindow.__init__`, replace:
```python
self.alert_panel = AlertPanel()
```

No changes needed—the `EnhancedAlertPanel` has the same public interface as `AlertPanel`.

### Step 3: Update the connection in `on_detections`

In `MainWindow.on_detections`, the existing code should work as-is:
```python
for incident in incidents_logged:
    self.alert_panel.add_incident(incident)
```

### Step 4: Update the connection for status changes

In `AlertPanel` callback (right panel action buttons), replace:
```python
self.alert_panel.update_incident_status(incident_id, new_status)
```

This already exists and works with the new panel.

---

## Architecture Overview

```
AlertItemWidget (one per incident)
├─ Header: [Emoji Icon] Event Title     HH:MM:SS     [Status Badge]
├─ Zone info + Confidence progress bar
├─ Recommendation (if available)
└─ Action buttons (Acknowledge / Resolve)

EnhancedAlertPanel (container)
├─ Summary bar: Open: N | Acked: M | Resolved: K
├─ Scrollable list of AlertItemWidgets (newest at top)
└─ Idle message (when no incidents)
```

---

## Key Features Explained

### 1. Severity Color Coding
Each alert has a left border matching its severity:
- **Critical** (#ff4444 red) — immediate action required
- **High** (#ff8c00 orange) — urgent attention needed
- **Medium** (#ffaa00 amber) — standard response
- **Low** (#88dd00 green) — informational

### 2. Confidence Visualization
A small progress bar (0–100%) shows how confident the AI is about the detection. Higher bars = higher confidence.

```
Confidence: [████████░░] 85%
```

### 3. Actionable Recommendations
The panel displays the `recommendation` field from `rules.py`, e.g.:
- Fire: "Evacuate immediately"
- No helmet: "Stop work, provide PPE"
- Intrusion: "Request identification"

### 4. Status Workflow
Incidents cycle through three states:
- **Open** (🔴): Just detected, requires attention
- **Acknowledged** (🟠): Operator confirmed, action in progress
- **Resolved** (🟢): Incident addressed, moved to history

### 5. Animation
New alerts slide in from the top with a smooth cubic-out easing curve over 300 ms.

---

## Message Clarity Improvements

### Before (current `alert_panel.py`)
```
restricted_area_intrusion detected in Warehouse Door
```

### After (enhanced panel)
```
🚨 Restricted Area Intrusion     13:45:22     [Open]
Zone: Warehouse Door
Confidence: [████████░░] 92%
✓ Request identification
[Acknowledge] [Resolve]
```

### Example Alert Messages

**Fire Detection (Critical)**
```
🚨 Fire Detected                 14:22:10     [Open]
Zone: Production Floor
Confidence: [██████████] 98%
✓ Evacuate immediately
[Acknowledge] [Resolve]
```

**No Helmet (Medium)**
```
⚡ No Helmet                      14:22:15     [Acknowledged]
Zone: Assembly Line
Confidence: [████████░░] 87%
✓ Stop work, provide PPE
[Resolve]
```

**Intrusion (High)**
```
⚠️ Restricted Area Intrusion     14:22:20     [Open]
Zone: Server Room
Confidence: [███████░░░] 76%
✓ Alert security, review access logs
[Acknowledge] [Resolve]
```

---

## Styling Customization

### Colors
Edit the `SEVERITY_COLORS` dict in `AlertItemWidget`:
```python
SEVERITY_COLORS = {
    "Critical": "#ff4444",  # Change to your brand red
    "High": "#ff8c00",      # etc.
    "Medium": "#ffaa00",
    "Low": "#88dd00",
}
```

### Icons
Change the `SEVERITY_ICONS` dict:
```python
SEVERITY_ICONS = {
    "Critical": "🚨",  # or "❌", "⛔", "🔴"
    "High": "⚠️",
    "Medium": "⚡",
    "Low": "ℹ️",
}
```

### Fonts
Modify the `QFont("Arial", 11)` calls for different typefaces/sizes.

### Animation Duration
Change `anim.setDuration(300)` (milliseconds) to speed up or slow down the slide-in.

---

## Testing the Enhancement

### Quick Test (no deployment)
1. Copy `enhanced_alert_panel.py` to `ui/`
2. In a test script, instantiate and populate:

```python
from PySide6.QtWidgets import QApplication
from ui.enhanced_alert_panel import EnhancedAlertPanel

app = QApplication([])
panel = EnhancedAlertPanel()

# Simulate an incident
panel.add_incident({
    "id": 1,
    "event_type": "fire",
    "severity": "Critical",
    "zone": "Warehouse",
    "confidence": 0.95,
    "timestamp": "2026-09-01 14:22:10",
    "recommendation": "Evacuate immediately",
    "status": "Open",
})

panel.show()
app.exec()
```

### Full Integration Test
1. Replace the import in `main_window.py`
2. Run the desktop app: `python main.py`
3. Trigger some events (use demo mode if model is unavailable)
4. Verify:
   - New alerts appear with animation
   - Colors match severity
   - Confidence bar displays correctly
   - Summary counts update
   - Acknowledge/Resolve buttons work

---

## Backward Compatibility

The `EnhancedAlertPanel` is a **drop-in replacement** for the old `AlertPanel`:
- Same signal names: `acknowledge_incident`, `resolve_incident`
- Same methods: `add_incident()`, `update_incident_status()`, `clear_all()`
- No changes needed in `main_window.py` except the import

---

## Future Enhancements

Ideas for further improvement (see `PROJECT_ANALYSIS_AND_ROADMAP.md` §7):

1. **Notification sound**: Play a beep when Critical incidents appear
2. **Toast notifications**: Pop-up toasts at screen corner (in addition to panel)
3. **Timeline view**: Chronological incident graph over the shift
4. **Auto-resolve**: Option to auto-mark incidents as resolved after N minutes
5. **Export**: Save incident reports as PDF/CSV
6. **Dark theme**: Alternative dark stylesheet for night shifts
7. **Mobile view**: Responsive layout for tablets/small screens
8. **Keyboard shortcuts**: Ctrl+A to acknowledge, Ctrl+R to resolve (focused alert)

---

## Troubleshooting

**Q: Alerts don't appear animated**
A: Check that `QTimer.singleShot` is being called. Ensure the Qt event loop is running.

**Q: Recommendation text is blank**
A: Verify that `rules.py` has an entry for the event type in `EVENT_RULES`. If missing, add it.

**Q: Colors look wrong**
A: Qt stylesheets may be overridden by the global app stylesheet. Check `MainWindow` for conflicting `setStyleSheet()` calls.

**Q: Panel takes up too much space**
A: Reduce `setMinimumWidth(320)` to something smaller (e.g., 250).

---

## API Reference

### EnhancedAlertPanel

```python
class EnhancedAlertPanel(QWidget):
    # Signals
    acknowledge_incident = pyqtSignal(int)  # incident_id
    resolve_incident = pyqtSignal(int)      # incident_id

    # Methods
    def add_incident(self, incident_dict: dict) -> None:
        """Add/update incident in the panel with animation."""

    def update_incident_status(self, incident_id: int, status: str) -> None:
        """Update status (Open/Acknowledged/Resolved)."""

    def clear_all(self) -> None:
        """Clear all alerts."""
```

### AlertItemWidget

```python
class AlertItemWidget(QFrame):
    # Signals
    acknowledge_clicked = pyqtSignal(int)   # incident_id
    resolve_clicked = pyqtSignal(int)       # incident_id

    # Class attributes
    SEVERITY_COLORS: dict[str, str]
    SEVERITY_ICONS: dict[str, str]
```

---

## Related Files

- `PROJECT_ANALYSIS_AND_ROADMAP.md` — Full technical overview and roadmap
- `main_window.py` — Integration point for the alert panel
- `rules.py` — Source of severity levels and recommendations
- `database.py` — Incident schema and persistence