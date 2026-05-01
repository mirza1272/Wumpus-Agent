from flask import Flask, jsonify, request, render_template
import random
import time

app = Flask(__name__)

# --- Logic Engine ---

class LogicKB:
    def __init__(self):
        self.clauses = set()
        self.inference_steps = 0

    def tell(self, clause):
        """Adds a clause (set of literals) to the KB."""
        if isinstance(clause, (list, set)):
            self.clauses.add(frozenset(clause))
        else:
            self.clauses.add(frozenset([clause]))

    def tell_formula(self, formula_type, head, neighbors):
        """
        Helper to add Wumpus World implications in CNF.
        formula_type: 'B' (Breeze) or 'S' (Stench)
        head: Literal like 'B_0_0' or '-B_0_0'
        neighbors: List of neighbor literals like ['P_0_1', 'P_1_0']
        """
        is_negated = head.startswith("-")
        symbol = head.lstrip("-")
        
        if not is_negated:
            # B <=> (P1 | P2 | ...)
            # 1. -B | P1 | P2 | ...
            self.tell({"-"+symbol} | set(neighbors))
            # 2. B | -P1, B | -P2, ...
            for n in neighbors:
                self.tell({symbol, "-"+n})
        else:
            # -B <=> -(P1 | P2 | ...) => -B <=> (-P1 & -P2 & ...)
            # This means if -B is true, all neighbors are not pits.
            for n in neighbors:
                self.tell("-"+n)

    def _negate(self, lit):
        return lit[1:] if lit.startswith("-") else "-" + lit

    def resolve(self, ci, cj):
        """Returns a set of all possible resolvents from two clauses."""
        resolvents = set()
        for di in ci:
            for dj in cj:
                if di == self._negate(dj):
                    res = set(ci) | set(cj)
                    res.remove(di)
                    res.remove(dj)
                    resolvents.add(frozenset(res))
        return resolvents

    def ask(self, query_literal):
        """
        Uses Resolution Refutation to prove query_literal.
        To prove alpha, we check if KB & ~alpha is unsatisfiable.
        Returns (True, steps) if proven, (False, steps) otherwise.
        """
        start_steps = self.inference_steps
        negated_query = self._negate(query_literal)
        clauses = set(self.clauses)
        clauses.add(frozenset([negated_query]))
        
        # Heuristic: Filter only relevant clauses
        # Only consider symbols within distance 1 or 2 of the query cell
        query_symbol = query_literal.lstrip("-")
        relevant_symbols = {query_symbol}
        
        # Parse query coords if possible (e.g., P_2_2)
        try:
            parts = query_symbol.split("_")
            if len(parts) == 3:
                r, c = int(parts[1]), int(parts[2])
                # Add percepts of immediate neighbors only
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1), (0,0)]:
                    nr, nc = r + dr, c + dc
                    relevant_symbols.add(f"P_{nr}_{nc}")
                    relevant_symbols.add(f"W_{nr}_{nc}")
                    relevant_symbols.add(f"B_{nr}_{nc}")
                    relevant_symbols.add(f"S_{nr}_{nc}")
        except:
            pass

        filtered_clauses = {c for c in clauses if any(l.lstrip("-") in relevant_symbols for l in c)}
        
        new = set()
        max_time = 1.5  # Reduced time for responsiveness
        start_time = time.time()
        
        while True:
            if time.time() - start_time > max_time: break
            
            n = len(filtered_clauses)
            if n > 200: break # Even smaller limit for speed
            
            clauses_list = list(filtered_clauses)
            added_any = False
            for i in range(len(clauses_list)):
                for j in range(i + 1, len(clauses_list)):
                    self.inference_steps += 1
                    resolvents = self.resolve(clauses_list[i], clauses_list[j])
                    
                    for res in resolvents:
                        if not res: # Empty set = contradiction
                            return True, self.inference_steps - start_steps
                        if res not in filtered_clauses:
                            new.add(res)
                            added_any = True
                    
                    if time.time() - start_time > max_time: break
                if time.time() - start_time > max_time: break
            
            if not added_any or new.issubset(filtered_clauses):
                break
            filtered_clauses.update(new)
            if len(filtered_clauses) > 300: break

        return False, self.inference_steps - start_steps

# --- Game Logic ---

game = {}

def get_neighbors(row, col, rows, cols):
    neighbors = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = row + dr, col + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            neighbors.append((nr, nc))
    return neighbors

def compute_percept(row, col):
    rows, cols = game["rows"], game["cols"]
    pits = game["pits"]
    wumpus = game["wumpus"]
    breeze = any(nb in pits for nb in get_neighbors(row, col, rows, cols))
    stench = any(nb == wumpus for nb in get_neighbors(row, col, rows, cols))
    return breeze, stench

def tell_percepts(row, col, breeze, stench):
    kb = game["kb"]
    rows, cols = game["rows"], game["cols"]
    neighbors = get_neighbors(row, col, rows, cols)
    
    # TELL the KB about the percept at (row, col)
    b_lit = f"B_{row}_{col}"
    s_lit = f"S_{row}_{col}"
    
    if breeze:
        kb.tell(b_lit)
    else:
        kb.tell("-"+b_lit)
        
    if stench:
        kb.tell(s_lit)
    else:
        kb.tell("-"+s_lit)

    # Rules: B_r_c <=> (P_n1 | P_n2 | ...)
    p_neighbors = [f"P_{nr}_{nc}" for nr, nc in neighbors]
    kb.tell_formula('B', b_lit if breeze else "-"+b_lit, p_neighbors)
    
    # Rules: S_r_c <=> (W_n1 | W_n2 | ...)
    w_neighbors = [f"W_{nr}_{nc}" for nr, nc in neighbors]
    kb.tell_formula('S', s_lit if stench else "-"+s_lit, w_neighbors)

def ask_safe(row, col):
    kb = game["kb"]
    # Check if we can prove NO Pit AND NO Wumpus
    is_not_pit, steps1 = kb.ask(f"-P_{row}_{col}")
    is_not_wumpus, steps2 = kb.ask(f"-W_{row}_{col}")
    
    # Also check if we can prove IT IS a Pit or Wumpus
    is_pit, _ = kb.ask(f"P_{row}_{col}")
    is_wumpus, _ = kb.ask(f"W_{row}_{col}")
    
    status = "unknown"
    if is_not_pit and is_not_wumpus:
        status = "safe"
    elif is_pit or is_wumpus:
        status = "danger"
        
    return status, steps1 + steps2

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    data = request.get_json()
    rows = int(data.get("rows", 4))
    cols = int(data.get("cols", 4))
    rows = max(2, min(rows, 8)) # Capped for performance
    cols = max(2, min(cols, 8))
    
    # Randomly place hazards (avoiding 0,0 only)
    all_cells = [(r, c) for r in range(rows) for c in range(cols) if (r, c) != (0,0)]
    num_pits = max(1, (rows * cols) // 5)
    pits = set(random.sample(all_cells, min(num_pits, len(all_cells))))
    
    remaining_cells = [c for c in all_cells if c not in pits]
    wumpus = random.choice(remaining_cells) if remaining_cells else None
    
    global game
    game = {
        "rows": rows,
        "cols": cols,
        "pits": pits,
        "wumpus": wumpus,
        "agent": (0, 0),
        "kb": LogicKB(),
        "visited": {(0, 0)},
        "status": "running",
        "log": ["Game started at (0,0)"],
        "inference_steps": 0,
        "percepts": [],
        "inferred_states": {} # (r,c) -> 'safe', 'danger', 'unknown'
    }
    
    # Initial knowledge: 0,0 is safe
    game["kb"].tell("-P_0_0")
    game["kb"].tell("-W_0_0")
    game["inferred_states"][(0,0)] = "safe"
    
    # First percept
    breeze, stench = compute_percept(0, 0)
    tell_percepts(0, 0, breeze, stench)
    game["percepts"] = (["Breeze"] if breeze else []) + (["Stench"] if stench else [])
    
    return jsonify(get_game_state())

@app.route("/next", methods=["POST"])
def next_move():
    try:
        if not game or game["status"] != "running":
            return jsonify({"error": "No active game"}), 400
        
        r, c = game["agent"]
        rows, cols = game["rows"], game["cols"]
        neighbors = get_neighbors(r, c, rows, cols)
        
        # 1. Try to find an unvisited safe neighbor
        target = None
        for nr, nc in neighbors:
            if (nr, nc) not in game["visited"]:
                state, steps = ask_safe(nr, nc)
                game["inference_steps"] += steps
                game["inferred_states"][(nr,nc)] = state
                if state == "safe":
                    target = (nr, nc)
                    break
        
        # 2. If no adjacent safe unvisited, BFS to nearest unvisited safe cell
        if not target:
            from collections import deque
            queue = deque([(r, c, [])])
            bfs_visited = {(r, c)}
            while queue:
                curr_r, curr_c, path = queue.popleft()
                if len(path) > 10: break # Depth limit
                
                for nr, nc in get_neighbors(curr_r, curr_c, rows, cols):
                    if (nr, nc) in bfs_visited: continue
                    bfs_visited.add((nr, nc))
                    
                    # Use cache if available
                    if (nr, nc) in game["inferred_states"]:
                        state = game["inferred_states"][(nr,nc)]
                    else:
                        state, steps = ask_safe(nr, nc)
                        game["inference_steps"] += steps
                        game["inferred_states"][(nr,nc)] = state
                    
                    if (nr, nc) in game["visited"] or state == "safe":
                        if (nr, nc) not in game["visited"] and state == "safe":
                            target = path[0] if path else (nr, nc)
                            break
                        queue.append((nr, nc, path + [(nr, nc)]))
                if target: break

        if not target:
            game["status"] = "stuck"
            game["log"].append("Agent stuck: No provably safe path to unvisited territory.")
            return jsonify(get_game_state())

        # Check if this is a backtracking move
        is_backtracking = target in game["visited"]
        if is_backtracking:
            game["log"].append(f"Backtracking through visited cell {target} to find a safe route.")

        # Move Agent
        game["agent"] = target
        game["visited"].add(target)
        
        # Check for death
        if target in game["pits"]:
            game["status"] = "dead"
            game["log"].append(f"Fell into a pit at {target}!")
        elif target == game["wumpus"]:
            game["status"] = "dead"
            game["log"].append(f"Eaten by the Wumpus at {target}!")
        else:
            breeze, stench = compute_percept(target[0], target[1])
            tell_percepts(target[0], target[1], breeze, stench)
            game["percepts"] = (["Breeze"] if breeze else []) + (["Stench"] if stench else [])
            game["log"].append(f"Moved to {target}. Percepts: {', '.join(game['percepts']) or 'None'}")
            
            # Check for win
            all_safe_cells = set((r, c) for r in range(rows) for c in range(cols) 
                                 if (r, c) not in game["pits"] and (r, c) != game["wumpus"])
            if all_safe_cells.issubset(game["visited"]):
                game["status"] = "win"
                game["log"].append("Goal Reached: All safe territory mapped.")

        return jsonify(get_game_state())
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

def get_game_state():
    grid = []
    for r in range(game["rows"]):
        row_data = []
        for c in range(game["cols"]):
            state = game["inferred_states"].get((r,c), "unknown")
            cell_type = "unknown"
            if (r, c) == game["agent"]:
                cell_type = "agent"
            elif (r, c) in game["visited"]:
                cell_type = "safe"
            elif state == "safe":
                cell_type = "safe_known"
            elif state == "danger":
                cell_type = "danger"
            
            # Reveal real hazards if game over
            if game["status"] in ["dead", "win", "stuck"]:
                if (r, c) in game["pits"] or (r, c) == game["wumpus"]:
                    cell_type = "hazard"
            
            row_data.append({
                "row": r, "col": c, "type": cell_type, 
                "percepts": game["inferred_states"].get((r,c), "")
            })
        grid.append(row_data)
        
    return {
        "grid": grid,
        "agent": {"row": game["agent"][0], "col": game["agent"][1]},
        "status": game["status"],
        "log": game["log"],
        "inference_steps": game["inference_steps"],
        "percepts": game["percepts"],
        "rows": game["rows"],
        "cols": game["cols"],
        "visited_count": len(game["visited"]),
        "safe_count": sum(1 for v in game["inferred_states"].values() if v == "safe")
    }

@app.route("/reset", methods=["POST"])
def reset():
    global game
    game = {}
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)