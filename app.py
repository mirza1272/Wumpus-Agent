from flask import Flask, jsonify, request, render_template
import random
import time
app = Flask(__name__)
class LogicKB:
    def __init__(self):
        self.clauses = []
        self.inference_steps = 0
    def tell(self, clause):
        if isinstance(clause, (list, set)):
            new_clause = tuple(sorted(list(clause)))
        else:
            new_clause = tuple([clause])
        if new_clause not in self.clauses:
            self.clauses.append(new_clause)
    def tell_formula(self, formula_type, head, neighbors):
        is_negated = head.startswith("-")
        symbol = head.lstrip("-")
        if not is_negated:
            c1 = ["-"+symbol]
            for n in neighbors:
                c1.append(n)
            self.tell(c1)
            for n in neighbors:
                self.tell([symbol, "-"+n])
        else:
            for n in neighbors:
                self.tell("-"+n)
    def _negate(self, lit):
        if lit.startswith("-"):
            return lit[1:]
        return "-" + lit
    def resolve(self, ci, cj):
        resolvents = []
        for di in ci:
            for dj in cj:
                if di == self._negate(dj):
                    res = list(set(list(ci) + list(cj)))
                    res.remove(di)
                    res.remove(dj)
                    resolvents.append(tuple(sorted(res)))
        return resolvents
    def ask(self, query_literal):
        start_steps = self.inference_steps
        negated_query = self._negate(query_literal)
        work_clauses = list(self.clauses)
        work_clauses.append(tuple([negated_query]))
        query_symbol = query_literal.lstrip("-")
        relevant_symbols = [query_symbol]
        try:
            parts = query_symbol.split("_")
            if len(parts) == 3:
                r, c = int(parts[1]), int(parts[2])
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1), (0,0)]:
                    nr, nc = r + dr, c + dc
                    relevant_symbols.append(f"P_{nr}_{nc}")
                    relevant_symbols.append(f"W_{nr}_{nc}")
                    relevant_symbols.append(f"B_{nr}_{nc}")
                    relevant_symbols.append(f"S_{nr}_{nc}")
        except:
            pass
        filtered = []
        for c in work_clauses:
            is_relevant = False
            for lit in c:
                if lit.lstrip("-") in relevant_symbols:
                    is_relevant = True
                    break
            if is_relevant:
                filtered.append(c)
        max_time = 1.5
        start_time = time.time()
        while True:
            if time.time() - start_time > max_time: break
            if len(filtered) > 200: break
            added_any = False
            new_rules = []
            n = len(filtered)
            for i in range(n):
                for j in range(i + 1, n):
                    self.inference_steps += 1
                    resolvents = self.resolve(filtered[i], filtered[j])
                    for res in resolvents:
                        if len(res) == 0:
                            return True, self.inference_steps - start_steps
                        if res not in filtered and res not in new_rules:
                            new_rules.append(res)
                            added_any = True
                    if time.time() - start_time > max_time: break
                if time.time() - start_time > max_time: break
            if not added_any: break
            for r in new_rules:
                filtered.append(r)
            if len(filtered) > 300: break
        return False, self.inference_steps - start_steps
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
    breeze = False
    for nb in get_neighbors(row, col, rows, cols):
        if nb in pits:
            breeze = True
            break
    stench = False
    for nb in get_neighbors(row, col, rows, cols):
        if nb == wumpus:
            stench = True
            break
    return breeze, stench
def tell_percepts(row, col, breeze, stench):
    kb = game["kb"]
    neighbors = get_neighbors(row, col, game["rows"], game["cols"])
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
    p_neighbors = []
    for nr, nc in neighbors:
        p_neighbors.append(f"P_{nr}_{nc}")
    kb.tell_formula('B', b_lit if breeze else "-"+b_lit, p_neighbors)
    w_neighbors = []
    for nr, nc in neighbors:
        w_neighbors.append(f"W_{nr}_{nc}")
    kb.tell_formula('S', s_lit if stench else "-"+s_lit, w_neighbors)
def ask_safe(row, col):
    kb = game["kb"]
    is_not_pit, steps1 = kb.ask(f"-P_{row}_{col}")
    is_not_wumpus, steps2 = kb.ask(f"-W_{row}_{col}")
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
    rows = max(2, min(int(data.get("rows", 4)), 8))
    cols = max(2, min(int(data.get("cols", 4)), 8))
    all_cells = []
    for r in range(rows):
        for c in range(cols):
            if (r, c) != (0, 0):
                all_cells.append((r, c))
    num_pits = max(1, (rows * cols) // 5)
    random.shuffle(all_cells)
    pits = all_cells[:num_pits]
    remaining = all_cells[num_pits:]
    wumpus = random.choice(remaining) if remaining else None
    global game
    game = {
        "rows": rows, "cols": cols, "pits": pits, "wumpus": wumpus,
        "agent": (0, 0), "kb": LogicKB(), "visited": [(0, 0)],
        "status": "running", "log": ["Game started at (0,0)"],
        "inference_steps": 0, "percepts": [], "inferred_states": {}
    }
    game["kb"].tell("-P_0_0")
    game["kb"].tell("-W_0_0")
    game["inferred_states"][(0,0)] = "safe"
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
        target = None
        for nr, nc in neighbors:
            if (nr, nc) not in game["visited"]:
                state, steps = ask_safe(nr, nc)
                game["inference_steps"] += steps
                game["inferred_states"][(nr,nc)] = state
                if state == "safe":
                    target = (nr, nc)
                    break
        if not target:
            from collections import deque
            queue = deque([(r, c, [])])
            bfs_visited = [(r, c)]
            while queue:
                curr_r, curr_c, path = queue.popleft()
                if len(path) > 10: break
                for nr, nc in get_neighbors(curr_r, curr_c, rows, cols):
                    if (nr, nc) in bfs_visited: continue
                    bfs_visited.append((nr, nc))
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
            game["log"].append("Agent stuck: No provably safe path.")
            return jsonify(get_game_state())
        is_backtracking = target in game["visited"]
        if is_backtracking:
            game["log"].append(f"Backtracking to {target}.")
        game["agent"] = target
        if target not in game["visited"]:
            game["visited"].append(target)
        if target in game["pits"]:
            game["status"] = "dead"
            game["log"].append(f"Fell into pit at {target}!")
        elif target == game["wumpus"]:
            game["status"] = "dead"
            game["log"].append(f"Eaten by Wumpus at {target}!")
        else:
            breeze, stench = compute_percept(target[0], target[1])
            tell_percepts(target[0], target[1], breeze, stench)
            game["percepts"] = (["Breeze"] if breeze else []) + (["Stench"] if stench else [])
            game["log"].append(f"Moved to {target}.")
            safe_cells = []
            for tr in range(rows):
                for tc in range(cols):
                    if (tr, tc) not in game["pits"] and (tr, tc) != game["wumpus"]:
                        safe_cells.append((tr, tc))
            all_visited = True
            for sc in safe_cells:
                if sc not in game["visited"]:
                    all_visited = False
                    break
            if all_visited:
                game["status"] = "win"
                game["log"].append("Win: All safe territory mapped.")
        return jsonify(get_game_state())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
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
            if game["status"] in ["dead", "win", "stuck"]:
                if (r, c) in game["pits"] or (r, c) == game["wumpus"]:
                    cell_type = "hazard"
            row_data.append({"row": r, "col": c, "type": cell_type})
        grid.append(row_data)
    safe_count = 0
    for v in game["inferred_states"].values():
        if v == "safe":
            safe_count += 1
    return {
        "grid": grid, "agent": {"row": game["agent"][0], "col": game["agent"][1]},
        "status": game["status"], "log": game["log"],
        "inference_steps": game["inference_steps"], "percepts": game["percepts"],
        "rows": game["rows"], "cols": game["cols"],
        "visited_count": len(game["visited"]), "safe_count": safe_count
    }
@app.route("/reset", methods=["POST"])
def reset():
    global game
    game = {}
    return jsonify({"status": "reset"})
if __name__ == "__main__":
    app.run(debug=True, port=5000)