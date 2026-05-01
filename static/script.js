let gameRunning = false;
function startGame() {
  const rows = parseInt(document.getElementById("inp-rows").value) || 5;
  const cols = parseInt(document.getElementById("inp-cols").value) || 5;
  fetch("/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows, cols })
  })
    .then(res => res.json())
    .then(data => {
      gameRunning = true;
      document.getElementById("btn-next").disabled = false;
      document.getElementById("btn-start").disabled = true;
      updateUI(data);
      addLog("System Initialized. Agent deployed.", "move");
    })
    .catch(err => {
      console.error("Start error:", err);
      addLog("Error: Could not start game.", "danger");
    });
}
function nextMove() {
  if (!gameRunning) return;
  fetch("/next", {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  })
    .then(res => res.json())
    .then(data => {
      updateUI(data);
      if (data.status !== "running") {
        document.getElementById("btn-next").disabled = true;
        gameRunning = false;
      }
    })
    .catch(err => {
      console.error("Next move error:", err);
      addLog("Error during inference.", "danger");
    });
}
function resetGame() {
  fetch("/reset", { method: "POST" })
    .then(() => {
      gameRunning = false;
      document.getElementById("btn-next").disabled = true;
      document.getElementById("btn-start").disabled = false;
      document.getElementById("grid-container").innerHTML = `
      <div class="grid-placeholder">
        <span class="ph-icon">⌗</span>
        <span>Configure and start the simulation</span>
      </div>
    `;
      document.getElementById("m-pos").textContent = "—";
      document.getElementById("m-steps").textContent = "0";
      document.getElementById("m-visited").textContent = "0";
      document.getElementById("m-safe").textContent = "0";
      document.getElementById("m-percept").textContent = "—";
      const badge = document.getElementById("status-badge");
      badge.textContent = "IDLE";
      badge.className = "status-badge";
      document.getElementById("log-feed").innerHTML = '<div class="log-entry">System Reset.</div>';
    });
}
function updateUI(data) {
  drawGrid(data.grid);
  document.getElementById("m-pos").textContent = `(${data.agent.row}, ${data.agent.col})`;
  document.getElementById("m-steps").textContent = data.inference_steps;
  document.getElementById("m-visited").textContent = data.visited_count;
  document.getElementById("m-safe").textContent = data.safe_count;
  document.getElementById("m-percept").textContent = data.percepts.join(", ") || "None";
  const badge = document.getElementById("status-badge");
  badge.textContent = data.status.toUpperCase();
  badge.className = `status-badge ${data.status}`;
  const logFeed = document.getElementById("log-feed");
  logFeed.innerHTML = "";
  data.log.forEach(msg => {
    const entry = document.createElement("div");
    entry.className = "log-entry";
    entry.textContent = msg;
    logFeed.appendChild(entry);
  });
  logFeed.scrollTop = logFeed.scrollHeight;
}
function drawGrid(grid) {
  const container = document.getElementById("grid-container");
  container.innerHTML = "";
  const table = document.createElement("table");
  table.className = "wumpus-grid";
  grid.forEach(row => {
    const tr = document.createElement("tr");
    row.forEach(cell => {
      const td = document.createElement("td");
      td.className = `cell cell-${cell.type}`;
      const content = document.createElement("div");
      content.className = "cell-content";
      if (cell.type === "agent") {
        content.innerHTML = "<b>A</b>";
      } else if (cell.type === "hazard") {
        content.innerHTML = "<b>X</b>";
      } else if (cell.type === "danger") {
        content.innerHTML = "?";
      }
      td.appendChild(content);
      tr.appendChild(td);
    });
    table.appendChild(tr);
  });
  container.appendChild(table);
}
function addLog(msg) {
  const logFeed = document.getElementById("log-feed");
  const entry = document.createElement("div");
  entry.className = "log-entry";
  entry.textContent = msg;
  logFeed.appendChild(entry);
  logFeed.scrollTop = logFeed.scrollHeight;
}
document.addEventListener("keydown", (e) => {
  if (e.code === "Space") {
    e.preventDefault();
    nextMove();
  }
  if (e.code === "Enter" && !gameRunning) {
    startGame();
  }
});