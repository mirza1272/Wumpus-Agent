from flask import Flask, jsonify, request, render_template
import random

app = Flask(__name__)

# ─── Global game state ────────────────────────────────────────────────────────
game = {}

def get_neighbors(row, col, rows, cols):
    neighbors = []
    if row > 0:
        neighbors.append((row - 1, col))
    if row < rows - 1:
        neighbors.append((row + 1, col))
    if col > 0:
        neighbors.append((row, col - 1))
    if col < cols - 1:
        neighbors.append((row, col + 1))
    return neighbors


# ─── Build percept for a cell ─────────────────────────────────────────────────
def compute_percept(row, col):
    rows = game["rows"]
    cols = game["cols"]
    pits = game["pits"]
    wumpus = game["wumpus"]

    breeze = False
    stench = False

    for nr, nc in get_neighbors(row, col, rows, cols):
        if (nr, nc) in pits:
            breeze = True
        if (nr, nc) == wumpus:
            stench = True

    return breeze, stench


# ─── TELL: add facts to KB ────────────────────────────────────────────────────
def tell(cell, breeze, stench):
    kb = game["kb"]
    row, col = cell

    # Mark cell as visited and safe
    kb["visited"].add(cell)
    kb["safe"].add(cell)

    # Store percept facts
    if breeze:
        kb["breeze_cells"].add(cell)
    if stench:
        kb["stench_cells"].add(cell)

    # If no breeze → all neighbors are pit-free
    if not breeze:
        rows = game["rows"]
        cols = game["cols"]
        for nb in get_neighbors(row, col, rows, cols):
            kb["no_pit"].add(nb)

    # If no stench → all neighbors are wumpus-free
    if not stench:
        rows = game["rows"]
        cols = game["cols"]
        for nb in get_neighbors(row, col, rows, cols):
            kb["no_wumpus"].add(nb)


# ─── Resolution refutation: is a cell safe? ───────────────────────────────────
def ask_safe(cell):
    kb = game["kb"]
    steps = 0

    # Already known safe
    if cell in kb["safe"]:
        steps += 1
        return True, steps

    # Proven no pit AND no wumpus → safe
    if cell in kb["no_pit"] and cell in kb["no_wumpus"]:
        steps += 2
        kb["safe"].add(cell)
        return True, steps

    # CNF-style resolution: check if we can derive "not pit" from clauses
    # Simple clause list: if any visited neighbor had no-breeze → neighbors not pit
    row, col = cell
    rows = game["rows"]
    cols = game["cols"]

    inferred_no_pit = False
    inferred_no_wumpus = False

    for nb in get_neighbors(row, col, rows, cols):
        steps += 1
        if nb in kb["visited"]:
            if nb not in kb["breeze_cells"]:
                inferred_no_pit = True
            if nb not in kb["stench_cells"]:
                inferred_no_wumpus = True

    # Contradiction check: if both inferred safe → resolve as safe
    if inferred_no_pit and inferred_no_wumpus:
        steps += 1
        kb["safe"].add(cell)
        return True, steps

    return False, steps


# ─── BFS: find path through safe cells to a safe-unvisited cell ───────────────
def bfs_to_unvisited():
    """
    BFS from current agent position through known-safe cells.
    Returns the first step toward any unvisited safe cell, or None.
    """
    agent = game["agent"]
    rows = game["rows"]
    cols = game["cols"]
    kb = game["kb"]

    from collections import deque
    visited_bfs = {agent}
    queue = deque()
    queue.append((agent, []))  # (cell, path_so_far)

    total_steps = 0

    while queue:
        current, path = queue.popleft()
        cr, cc = current

        for nb in get_neighbors(cr, cc, rows, cols):
            if nb in visited_bfs:
                continue
            visited_bfs.add(nb)

            # Only travel through safe cells
            is_safe, steps = ask_safe(nb)
            total_steps += steps

            if not is_safe:
                continue

            new_path = path + [nb]

            # Found an unvisited safe cell
            if nb not in kb["visited"]:
                game["inference_steps"] += total_steps
                # Return the first step in the path
                return new_path[0] if new_path else nb

            # Keep BFS-ing through visited safe cells
            queue.append((nb, new_path))

    game["inference_steps"] += total_steps
    return None


# ─── Pick next move for agent ─────────────────────────────────────────────────
def pick_next_move():
    agent = game["agent"]
    rows = game["rows"]
    cols = game["cols"]
    kb = game["kb"]

    row, col = agent
    neighbors = get_neighbors(row, col, rows, cols)

    total_steps = 0
    safe_unvisited = []

    # Check each direct neighbor first
    for nb in neighbors:
        is_safe, steps = ask_safe(nb)
        total_steps += steps
        if is_safe and nb not in kb["visited"]:
            safe_unvisited.append(nb)

    game["inference_steps"] += total_steps

    if safe_unvisited:
        return safe_unvisited[0], "move"

    # No direct safe-unvisited neighbor → BFS through known-safe cells
    next_cell = bfs_to_unvisited()
    if next_cell is not None:
        return next_cell, "backtrack"

    return None, "stuck"


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start():
    data = request.get_json()
    rows = int(data.get("rows", 4))
    cols = int(data.get("cols", 4))

    # Clamp grid size
    rows = max(2, min(rows, 10))
    cols = max(2, min(cols, 10))

    # Place pits randomly (skip (0,0))
    all_cells = [(r, c) for r in range(rows) for c in range(cols) if (r, c) != (0, 0)]
    num_pits = max(1, (rows * cols) // 5)
    pits = set(map(tuple, random.sample(all_cells, min(num_pits, len(all_cells) - 1))))

    # Place wumpus (not at (0,0), not in pit)
    safe_for_wumpus = [c for c in all_cells if c not in pits]
    wumpus = tuple(random.choice(safe_for_wumpus))

    # Gold (optional flavor — not used in logic)
    remaining = [c for c in safe_for_wumpus if c != wumpus]
    gold = tuple(random.choice(remaining)) if remaining else None

    # Init knowledge base
    kb = {
        "visited": set(),
        "safe": set(),
        "breeze_cells": set(),
        "stench_cells": set(),
        "no_pit": set(),
        "no_wumpus": set(),
    }

    global game
    game = {
        "rows": rows,
        "cols": cols,
        "pits": pits,
        "wumpus": wumpus,
        "gold": gold,
        "agent": (0, 0),
        "kb": kb,
        "inference_steps": 0,
        "status": "running",
        "log": [],
    }

    # Agent starts at (0,0) — TELL initial percept
    breeze, stench = compute_percept(0, 0)
    tell((0, 0), breeze, stench)

    return jsonify(build_response("Game started! Agent at (0,0)."))


@app.route("/next", methods=["POST"])
def next_move():
    if not game:
        return jsonify({"error": "No game running"}), 400
    if game["status"] != "running":
        return jsonify(build_response("Game already ended.")), 200

    next_cell, action = pick_next_move()

    if action == "stuck":
        game["status"] = "stuck"
        game["log"].append("No safe move available. Agent is stuck!")
        return jsonify(build_response("Stuck — no safe move found."))

    # Move agent
    game["agent"] = next_cell
    row, col = next_cell

    # Check death
    if next_cell in game["pits"]:
        game["status"] = "dead"
        game["log"].append(f"Agent fell into a pit at {next_cell}!")
        return jsonify(build_response(f"Agent died in a pit at ({row},{col})!"))

    if next_cell == game["wumpus"]:
        game["status"] = "dead"
        game["log"].append(f"Agent eaten by Wumpus at {next_cell}!")
        return jsonify(build_response(f"Agent eaten by Wumpus at ({row},{col})!"))

    # TELL new percept
    breeze, stench = compute_percept(row, col)
    tell(next_cell, breeze, stench)

    msg = f"Moved to ({row},{col})."
    if breeze:
        msg += " Breeze felt!"
    if stench:
        msg += " Stench detected!"
    game["log"].append(msg)

    # Check win: all non-hazard cells reachable and visited
    all_cells = {(r, c) for r in range(game["rows"]) for c in range(game["cols"])}
    hazards = game["pits"] | {game["wumpus"]}
    safe_cells = all_cells - hazards
    if game["kb"]["visited"] >= safe_cells:
        game["status"] = "win"
        msg += " 🏆 All safe cells explored — Agent WINS!"

    return jsonify(build_response(msg))


@app.route("/reset", methods=["POST"])
def reset():
    global game
    game = {}
    return jsonify({"status": "reset"})


# ─── Build JSON response ──────────────────────────────────────────────────────
def build_response(message):
    kb = game["kb"]
    rows = game["rows"]
    cols = game["cols"]
    agent = game["agent"]
    pits = game["pits"]
    wumpus = game["wumpus"]
    status = game["status"]

    # Build grid info for frontend
    grid = []
    for r in range(rows):
        row_data = []
        for c in range(cols):
            cell = (r, c)
            if cell == agent:
                cell_type = "agent"
            elif cell in kb["visited"]:
                cell_type = "safe"
            elif cell in kb["safe"]:
                cell_type = "safe"
            elif cell in pits or cell == wumpus:
                # Only reveal danger if game ended
                if status in ("dead", "win", "stuck"):
                    cell_type = "danger"
                else:
                    cell_type = "unknown"
            else:
                cell_type = "unknown"

            percept = []
            if cell in kb["breeze_cells"]:
                percept.append("B")
            if cell in kb["stench_cells"]:
                percept.append("S")

            row_data.append({
                "type": cell_type,
                "percept": ",".join(percept),
                "row": r,
                "col": c
            })
        grid.append(row_data)

    # Current percept at agent position
    cur_breeze = agent in kb["breeze_cells"]
    cur_stench = agent in kb["stench_cells"]
    current_percept = []
    if cur_breeze:
        current_percept.append("Breeze")
    if cur_stench:
        current_percept.append("Stench")
    if not current_percept:
        current_percept.append("None")

    return {
        "grid": grid,
        "agent": {"row": agent[0], "col": agent[1]},
        "rows": rows,
        "cols": cols,
        "status": status,
        "message": message,
        "inference_steps": game["inference_steps"],
        "visited_count": len(kb["visited"]),
        "safe_count": len(kb["safe"]),
        "current_percept": current_percept,
        "log": game["log"][-5:],  # last 5 log entries
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
