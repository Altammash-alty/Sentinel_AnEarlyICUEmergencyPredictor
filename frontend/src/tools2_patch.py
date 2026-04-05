import re
import os

filepath = r"c:\Users\mdalt\OneDrive\Desktop\Sentinel\frontend\src\index.css"

with open(filepath, 'r', encoding='utf-8') as f:
    css = f.read()

# 1. Update Variables
vars_code = """
:root {
  --bg-base:        #080b12;
  --bg-surface:     #0e1420;
  --bg-elevated:    #141b2d;
  --bg-border:      #1e2a3a;

  --text-primary:   #e2e8f0;
  --text-secondary: #64748b;
  --text-muted:     #334155;

  --accent-primary: #0ea5e9;
  --accent-glow:    rgba(14,165,233,0.15);

  --status-stable:  #10b981;
  --status-warning: #f59e0b;
  --status-critical:#ef4444;

  --bg:        var(--bg-base);
  --surface:   var(--bg-surface);
  --surface2:  var(--bg-elevated);
  --border:    var(--bg-border);
  --border2:   var(--bg-border);
  --green:     var(--status-stable);
  --amber:     var(--status-warning);
  --red:       var(--status-critical);
  --blue:      var(--accent-primary);
  --text:      var(--text-primary);
  --muted:     var(--text-secondary);
  --muted2:    var(--text-muted);

  --font-mono: 'JetBrains Mono', monospace;
  --font-body: 'Inter', sans-serif;
  --radius:    8px;
  --radius-sm: 4px;
  --radius-lg: 12px;
  --bar-h:     52px;
  --transition: 0.2s ease;
}
"""
css = re.sub(r':root\s*\{[^}]+\}', vars_code.strip(), css, count=1)

# Status bar
css = re.sub(
    r'.status-bar\s*\{[^}]+\}',
    """.status-bar {
  position: fixed; top: 0; left: 0; right: 0;
  height: var(--bar-h);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; z-index: 1000; gap: 16px;
}""", css
)

# Patient Card
css = re.sub(
    r'.patient-card\s*\{[^}]+\}',
    """.patient-card {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: box-shadow 0.4s ease, border-color 0.4s ease;
  overflow: hidden;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.03);
}""", css
)

# Panels
css = re.sub(
    r'.panel\s*\{[^}]+\}',
    """.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.03);
  display: flex;
  flex-direction: column;
}""", css
)

# Tooltip
css = css.replace("box-shadow: var(--tooltip-shadow, 0 8px 24px rgba(0,0,0,0.6));", "")

# Pulse animation for critical RiskBadge
pulse_anim = """
@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
}

.pulse {
  animation: pulse 2s ease-in-out infinite;
}
"""
css += pulse_anim

# Filter buttons
css = re.sub(r'\.filter-tab\.active,\s*\.filter-tab:hover\s*\{[^}]+\}', """.filter-tab.active, .filter-tab:hover {
  background: rgba(14,165,233,0.10);
  color: var(--blue);
  border-color: rgba(14,165,233,0.30);
}""", css)

# Alert cards
css = re.sub(r'\.alert-card\s*\{[^}]+\}', """.alert-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  display: flex; flex-direction: column; gap: 6px;
  margin-bottom: 8px;
}""", css)

# Acknowledge button
css = re.sub(r'\.ack-btn\s*\{[^}]+\}', """.ack-btn {
  align-self: flex-start;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  transition: all var(--transition);
}""", css)
css = re.sub(r'\.ack-btn:hover\s*\{\s*background:\s*[^;]+;\s*\}', """.ack-btn:hover { background: transparent; border-color: var(--green); color: var(--green); }""", css)

# Telemetry
css = re.sub(r'\.telemetry-row\s*\{[^}]+\}', """.telemetry-row {
  display: flex; align-items: center; gap: 10px; padding: 7px 16px;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  flex-wrap: wrap;
}""", css)
css = re.sub(r'\.telemetry-corrected\s*\{[^}]+\}', """.telemetry-corrected {
  background: rgba(245,158,11,0.05);
  border-left: 2px solid var(--amber);
  color: var(--amber);
}""", css)
css = re.sub(r'\.hex-chunk\s*\{[^}]+\}', """.hex-chunk {
  padding: 2px 4px; border-radius: 2px; color: #1e4a6e;
}""", css)

# Remove Light Theme entirely to simplify
css = re.sub(r'\/\* ════+ \n   LIGHT THEME OVERRIDES.*', '', css, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(css)
