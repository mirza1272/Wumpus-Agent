# 🕵️ Wumpus World: Knowledge-Based Logic Agent

A web-based **Dynamic Pathfinding Agent** that uses **Propositional Logic** and **Resolution Refutation** to navigate a hazardous grid. The agent starts with zero knowledge and must deduce safe paths using percepts (Breeze/Stench) collected during exploration.

---

## 🛠️ Technology Stack
- **Backend**: Python 3 with Flask
- **Frontend**: HTML5, Vanilla CSS3 (Simple Brown Theme), JavaScript (ES6)
- **Logic**: Propositional Logic Knowledge Base (CNF)
- **Inference**: Automated Resolution Refutation

---

## 🧠 Core Features

### 1. Propositional Logic Engine
The agent maintains a formal **Knowledge Base (KB)**. When it perceives a Breeze or Stench, it "TELLS" the KB new rules in Conjunctive Normal Form (CNF):
- `Breeze(x,y) ⇔ Pit(neighbor1) ∨ Pit(neighbor2) ∨ ...`
- `Stench(x,y) ⇔ Wumpus(neighbor1) ∨ Wumpus(neighbor2) ∨ ...`

### 2. Resolution Refutation
Before every move, the agent "ASKS" the KB if a neighbor is safe by attempting to find a contradiction:
- To prove a cell is safe from Pits, it assumes `Pit(x,y)` is true and tries to resolve a contradiction (`empty clause`).
- **Optimization**: To ensure high performance, the engine uses **Localized Inference**, only considering clauses within a 1-cell radius of the target.

### 3. Smart Pathfinding & Backtracking
- **Safety First**: The agent will never move into an unknown cell unless it can be proven safe.
- **Backtracking**: If all neighbors are unknown or dangerous, the agent uses a BFS (Breadth-First Search) through already-visited safe cells to find the nearest unvisited safe territory.
- **Stuck Detection**: If no provably safe path exists on the entire explored map, the agent triggers a **STUCK** status to avoid taking risks.

---

## 🎨 Visualization Legend

The grid is color-coded based on the agent's current knowledge:

| Color | Status | Description |
| :--- | :--- | :--- |
| 🟩 **Green** | **Safe** | Cells that are visited or proven safe via logic. |
| ⬜ **Gray** | **Unknown** | Unvisited cells with no conclusive evidence yet. |
| 🟥 **Red** | **Hazard** | Confirmed Pits, the Wumpus, or dangerous territory. |
| 🟨 **Beige** | **Agent** | The current location of the Agent (marked with **A**). |

---

## 📁 Project Structure

```text
wumpus_agent/
├── app.py              # Flask Server, LogicKB class, and Game Logic
├── templates/
│   └── index.html      # Simple UI Structure
├── static/
│   ├── style.css       # Simple Brown/Red Design System
│   └── script.js       # Frontend Grid Rendering & API Integration
└── requirements.txt    # Flask dependency
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python installed. You will also need Flask:
```bash
pip install flask
```

### 2. Installation
1. Clone or download this repository.
2. Navigate to the project folder.

### 3. Run the Application
```bash
python app.py
```
4. Open your browser and go to `http://127.0.0.1:5000`.

---

## 📊 Telemetry Metrics
- **Coordinates**: Real-time (x, y) position of the agent.
- **Inference Steps**: Counts every resolution operation performed by the AI.
- **Exploration %**: Percentage of the safe grid successfully mapped.
- **Active Percepts**: Displays "Breeze" or "Stench" felt at the current position.

---

## 📜 License
This project was developed as an AI Assignment for exploring Knowledge-Based Agents and Propositional Logic.
