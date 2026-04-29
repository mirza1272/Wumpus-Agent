# 🕹️ Dynamic Wumpus Logic Agent

A **Knowledge-Based AI Agent** that navigates the Wumpus World using
**Propositional Logic**, **TELL/ASK inference**, and **Resolution Refutation**.

Built with **Python Flask** (backend) + **Vanilla HTML/CSS/JS** (frontend).

---

## 📁 Folder Structure

```
wumpus_agent/
├── app.py                  ← Flask server + KB logic + game engine
├── requirements.txt        ← Python dependencies
├── templates/
│   └── index.html          ← Main web page
├── static/
│   ├── style.css           ← All styling (dark terminal theme)
│   └── script.js           ← Frontend logic (grid draw, API calls)
└── README.md               ← This file
```

---

## 🚀 How to Run

### 1. Install Python 3 (if not already installed)
Download from https://python.org

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the server
```bash
python app.py
```

### 4. Open in browser
```
http://localhost:5000
```

---

## 🎮 How to Play

1. Enter grid **Rows** and **Cols** (2–10)
2. Click **▶ START GAME** — grid generates with random pits + Wumpus
3. Click **⟶ NEXT MOVE** to step the agent one move at a time
4. Press **SPACE** as keyboard shortcut for next move
5. Click **↺ RESET** to start fresh

---

## 🧠 AI Logic Explained

### Knowledge Base (KB)
The agent maintains a KB with:
- `visited` — cells the agent has been to
- `safe` — cells proven safe
- `breeze_cells` — cells where breeze was felt
- `stench_cells` — cells where stench was detected
- `no_pit` — cells proven pit-free
- `no_wumpus` — cells proven Wumpus-free

### TELL
When the agent enters a cell, it **TELLs** the KB:
- Breeze → some adjacent cell might have a pit
- No breeze → all adjacent cells are definitely pit-free
- Stench → some adjacent cell might have a Wumpus
- No stench → all adjacent cells are definitely Wumpus-free

### ASK (Resolution Refutation)
Before moving to a neighbor, the agent **ASKs** the KB:
> "Is this cell safe?"

The resolution steps:
1. Check if already in `safe` set → trivially true
2. Check if in both `no_pit` AND `no_wumpus` → directly proven safe
3. CNF-style resolution: scan all visited neighbors of the candidate cell.
   If any visited neighbor had **no breeze** → candidate is pit-free.
   If any visited neighbor had **no stench** → candidate is Wumpus-free.
   If both inferred → contradiction resolved → cell is SAFE.

Each check increments the **inference steps counter**.

### Grid Colors
| Color | Meaning |
|-------|---------|
| 🔵 Blue | Agent current position |
| 🟢 Green | Safe / visited cell |
| ⬛ Gray | Unknown cell |
| 🔴 Red | Confirmed danger (shown after death/win) |

### Percept Tags
| Tag | Meaning |
|-----|---------|
| **B** | Breeze felt (cyan badge) |
| **S** | Stench detected (yellow badge) |

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Next Move (when game running) |
| `Enter` | Start Game (when idle) |

---

## 📊 Metrics Dashboard

| Metric | Description |
|--------|-------------|
| Agent Position | Current (row, col) |
| Inference Steps | Total KB resolution operations |
| Visited Cells | How many cells explored |
| Safe Cells | Total cells in KB proven safe |
| Current Percepts | Breeze / Stench / None at current cell |

---

## 🏆 Win / Lose Conditions

- **WIN** — Agent visits all non-hazard cells on the grid
- **DEAD** — Agent walks into a pit or the Wumpus cell
- **STUCK** — No safe unvisited neighbor found (agent stops safely)
