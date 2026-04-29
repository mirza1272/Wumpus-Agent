// ─── Simple state ──────────────────────────────────────────────────
var gameRunning = false;

// ─── Start game ────────────────────────────────────────────────────
function startGame() {
  var rows = parseInt(document.getElementById("inp-rows").value) || 5;
  var cols = parseInt(document.getElementById("inp-cols").value) || 5;

  // Basic clamp
  if (rows < 2) rows = 2;
  if (rows > 10) rows = 10;
  if (cols < 2) cols = 2;
  if (cols > 10) cols = 10;

  fetch("/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows: rows, cols: cols })
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    gameRunning = true;
    document.getElementById("btn-next").disabled = false;
    updateUI(data);
    addLog("Game initialized — Agent placed at (0,0).", "move");
  })
  .catch(function(err) {
    console.error("Start error:", err);
    addLog("Error starting game. Check server.", "danger");
  });
}

// ─── Next move ─────────────────────────────────────────────────────
function nextMove() {
  if (!gameRunning) return;

  fetch("/next", {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  })
  .then(function(res) { return res.json(); })
  .then(function(data) {
    updateUI(data);

    // Decide log style
    var status = data.status;
    var cls = "move";
    if (status === "dead")  cls = "danger";
    if (status === "stuck") cls = "warn";
    if (status === "win")   cls = "move";

    addLog(data.message, cls);

    // Disable next move if game ended
    if (status !== "running") {
      document.getElementById("btn-next").disabled = true;
      gameRunning = false;
    }
  })
  .catch(function(err) {
    console.error("Next move error:", err);
    addLog("Error during move. Check server.", "danger");
  });
}

// ─── Reset game ─────────────────────────────────────────────────────
function resetGame() {
  fetch("/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  })
  .then(function() {
    gameRunning = false;
    document.getElementById("btn-next").disabled = true;

    // Clear grid
    var container = document.getElementById("grid-container");
    container.innerHTML =
      '<div class="grid-placeholder"><span class="ph-icon">⊞</span><span>Configure and start the simulation</span></div>';

    // Reset metrics
    document.getElementById("m-pos").textContent     = "—";
    document.getElementById("m-steps").textContent   = "0";
    document.getElementById("m-visited").textContent = "0";
    document.getElementById("m-safe").textContent    = "0";
    document.getElementById("m-percept").textContent = "—";

    // Reset status
    var badge = document.getElementById("status-badge");
    badge.textContent = "IDLE";
    badge.className = "status-badge";
    document.getElementById("status-msg").textContent = "Configure grid and press START.";

    // Clear log
    document.getElementById("log-feed").innerHTML =
      '<div class="log-entry idle">System reset. Ready.</div>';
  })
  .catch(function(err) { console.error("Reset error:", err); });
}

// ─── Update entire UI from server response ──────────────────────────
function updateUI(data) {
  // Draw grid
  drawGrid(data.grid, data.rows, data.cols);

  // Update metrics
  document.getElementById("m-pos").textContent     = "(" + data.agent.row + "," + data.agent.col + ")";
  document.getElementById("m-steps").textContent   = data.inference_steps;
  document.getElementById("m-visited").textContent = data.visited_count;
  document.getElementById("m-safe").textContent    = data.safe_count;
  document.getElementById("m-percept").textContent = data.current_percept.join(", ");

  // Update status badge
  var badge = document.getElementById("status-badge");
  var status = data.status;
  badge.className = "status-badge " + status;

  var labels = {
    "running": "RUNNING",
    "win":     "AGENT WINS 🏆",
    "dead":    "AGENT DEAD 💀",
    "stuck":   "STUCK ⚠",
    "idle":    "IDLE"
  };
  badge.textContent = labels[status] || status.toUpperCase();
  document.getElementById("status-msg").textContent = data.message;

  // Update recent log from server
  if (data.log && data.log.length > 0) {
    // We add last server log entry; the manual addLog handles newest
  }
}

// ─── Draw the grid ──────────────────────────────────────────────────
function drawGrid(grid, rows, cols) {
  var container = document.getElementById("grid-container");

  // Build table HTML
  var html = '<table class="wumpus-grid"><tbody>';

  for (var r = 0; r < rows; r++) {
    html += '<tr>';
    for (var c = 0; c < cols; c++) {
      var cell = grid[r][c];
      var cssClass = getCellClass(cell.type);
      var icon     = getCellIcon(cell.type);
      var percepts = buildPerceptTags(cell.percept);

      html += '<td class="' + cssClass + '">';
      html +=   '<span class="cell-icon">' + icon + '</span>';
      html +=   '<span class="cell-coords">' + r + ',' + c + '</span>';
      if (percepts) {
        html += '<span class="cell-percepts">' + percepts + '</span>';
      }
      html += '</td>';
    }
    html += '</tr>';
  }

  html += '</tbody></table>';
  container.innerHTML = html;
}

// ─── Get CSS class for cell type ───────────────────────────────────
function getCellClass(type) {
  var map = {
    "agent":   "cell-agent",
    "safe":    "cell-safe",
    "unknown": "cell-unknown",
    "danger":  "cell-danger"
  };
  return map[type] || "cell-unknown";
}

// ─── Get icon emoji for cell type ──────────────────────────────────
function getCellIcon(type) {
  var map = {
    "agent":   "🤖",
    "safe":    "✓",
    "unknown": "?",
    "danger":  "💀"
  };
  return map[type] || "?";
}

// ─── Build percept tag HTML ─────────────────────────────────────────
function buildPerceptTags(percept) {
  if (!percept) return "";
  var html = "";
  var parts = percept.split(",");
  for (var i = 0; i < parts.length; i++) {
    var p = parts[i].trim();
    if (p === "B") html += '<span class="p-tag pb">B</span>';
    if (p === "S") html += '<span class="p-tag ps">S</span>';
  }
  return html;
}

// ─── Add entry to agent log ─────────────────────────────────────────
function addLog(message, type) {
  var feed = document.getElementById("log-feed");
  var div  = document.createElement("div");
  div.className = "log-entry " + (type || "move");

  // Add timestamp
  var now = new Date();
  var ts  = "[" + pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds()) + "] ";
  div.textContent = ts + message;

  feed.appendChild(div);

  // Keep only last 30 entries
  while (feed.children.length > 30) {
    feed.removeChild(feed.firstChild);
  }

  // Scroll to bottom
  feed.scrollTop = feed.scrollHeight;
}

// ─── Pad single digit ───────────────────────────────────────────────
function pad(n) {
  return n < 10 ? "0" + n : "" + n;
}

// ─── Keyboard shortcut ──────────────────────────────────────────────
document.addEventListener("keydown", function(e) {
  // Press Space to trigger next move
  if (e.code === "Space" && gameRunning) {
    e.preventDefault();
    nextMove();
  }
  // Press Enter to start
  if (e.code === "Enter" && !gameRunning) {
    startGame();
  }
});
