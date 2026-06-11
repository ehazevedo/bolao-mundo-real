(function () {
  let data = window.BOLAO_DATA || { matches: [], participants: [], rules: {} };
  const publishedResults = window.BOLAO_RESULTS || {};
  const config = window.BOLAO_CONFIG || {};
  const isLocalHost = ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
  const isAdmin = isLocalHost;
  let results = { ...publishedResults };

  const tabs = document.querySelectorAll(".tab");
  const views = document.querySelectorAll(".view");
  const leaderboardBody = document.querySelector("#leaderboard tbody");
  const resultsGrid = document.querySelector("#resultsGrid");
  const matchBetsBoard = document.querySelector("#matchBetsBoard");
  const participantSelect = document.querySelector("#participantSelect");
  const participantBetsBody = document.querySelector("#participantBets tbody");
  const statusMessage = document.querySelector("#statusMessage");
  const resultsStatusMessage = document.querySelector("#resultsStatusMessage");

  document.body.classList.toggle("admin-mode", isAdmin);

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => item.classList.remove("active"));
      views.forEach((view) => view.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.tab).classList.add("active");
    });
  });

  document.getElementById("resetResults").addEventListener("click", () => {
    if (!confirm("Limpar todos os resultados digitados neste navegador?")) return;
    Object.keys(results).forEach((key) => delete results[key]);
    renderAll();
  });

  document.getElementById("refreshBets").addEventListener("click", async () => {
    await refreshBetsFromFolder();
  });

  participantSelect.addEventListener("change", renderParticipantBets);

  renderAll();
  loadSheetResults();

  function renderAll() {
    renderMetrics();
    renderLeaderboard();
    renderResultsGrid();
    renderMatchBetsBoard();
    renderParticipantSelect();
    renderParticipantBets();
  }

  async function refreshBetsFromFolder() {
    if (window.location.protocol === "file:") {
      showStatus(
        statusMessage,
        "Para ler novos arquivos da pasta apostas, abra pelo servidor local: python3 scripts/server.py",
        "error",
      );
      return;
    }

    showStatus(statusMessage, "Lendo a pasta apostas e atualizando a base...", "");
    try {
      const response = await fetch("/api/import-bets", { method: "POST" });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Não foi possível atualizar os palpites.");
      }
      data = payload.data;
      window.BOLAO_DATA = payload.data;
      renderAll();
      showStatus(statusMessage, `Palpites atualizados: ${data.participants.length} participante(s) e ${data.matches.length} jogo(s).`, "success");
    } catch (error) {
      showStatus(statusMessage, `Erro ao atualizar palpites: ${error.message}`, "error");
    }
  }

  async function loadSheetResults() {
    if (!config.googleSheetId) return;

    try {
      const sheetResults = await fetchGoogleSheetResults(config.googleSheetId, config.googleSheetGid || "0");
      results = sheetResults;
      renderAll();
      showStatus(resultsStatusMessage, `Resultados carregados do Google Sheets: ${Object.keys(results).length} jogo(s).`, "success");
    } catch (error) {
      showStatus(resultsStatusMessage, `Não consegui carregar o Google Sheets; usando fallback publicado. Detalhe: ${error.message}`, "error");
    }
  }

  function fetchGoogleSheetResults(sheetId, gid) {
    return new Promise((resolve, reject) => {
      const callbackName = `__bolaoSheetCallback${Date.now()}${Math.floor(Math.random() * 1000)}`;
      const timeout = window.setTimeout(() => {
        cleanup();
        reject(new Error("tempo limite ao ler a planilha"));
      }, 12000);

      const script = document.createElement("script");
      const url = new URL(`https://docs.google.com/spreadsheets/d/${encodeURIComponent(sheetId)}/gviz/tq`);
      url.searchParams.set("gid", gid);
      url.searchParams.set("tqx", `out:json;responseHandler:${callbackName}`);
      url.searchParams.set("tq", "select *");
      script.src = url.toString();
      script.onerror = () => {
        cleanup();
        reject(new Error("a planilha não está pública ou não respondeu"));
      };

      window[callbackName] = (payload) => {
        cleanup();
        try {
          resolve(parseGoogleSheetPayload(payload));
        } catch (error) {
          reject(error);
        }
      };

      function cleanup() {
        window.clearTimeout(timeout);
        delete window[callbackName];
        script.remove();
      }

      document.head.appendChild(script);
    });
  }

  function parseGoogleSheetPayload(payload) {
    if (!payload || !payload.table) {
      throw new Error("resposta inválida da planilha");
    }

    const headers = (payload.table.cols || []).map((col, index) => normalizeHeader(col.label || col.id || `col${index}`));
    let matchIdIndex = findHeader(headers, ["matchid", "jogo", "match", "id"]);
    let g1Index = findHeader(headers, ["g1", "placar1", "gols1", "time1", "casa"]);
    let g2Index = findHeader(headers, ["g2", "placar2", "gols2", "time2", "fora"]);

    if (matchIdIndex < 0 || g1Index < 0 || g2Index < 0) {
      matchIdIndex = 0;
      g1Index = 1;
      g2Index = 2;
    }

    const nextResults = {};
    (payload.table.rows || []).forEach((row) => {
      const cells = row.c || [];
      const matchId = numberFromCell(cells[matchIdIndex]);
      const g1 = numberFromCell(cells[g1Index]);
      const g2 = numberFromCell(cells[g2Index]);
      if (!Number.isInteger(matchId)) return;
      if (!Number.isInteger(g1) || !Number.isInteger(g2)) return;
      nextResults[String(matchId)] = { g1, g2 };
    });

    return nextResults;
  }

  function normalizeHeader(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-zA-Z0-9]/g, "")
      .toLowerCase();
  }

  function findHeader(headers, candidates) {
    return headers.findIndex((header) => candidates.includes(header));
  }

  function numberFromCell(cell) {
    if (!cell || cell.v === null || cell.v === undefined || cell.v === "") return null;
    const value = Number(cell.v);
    return Number.isFinite(value) ? value : null;
  }

  function showStatus(target, message, kind) {
    if (!target) return;
    target.textContent = message;
    target.className = `status-message active ${kind || ""}`.trim();
    if (kind === "success") {
      window.setTimeout(() => {
        if (target.textContent === message) target.className = "status-message";
      }, 4000);
    }
  }

  function resultCode(g1, g2) {
    if (g1 > g2) return "H";
    if (g1 < g2) return "A";
    return "D";
  }

  function matchResult(matchId) {
    const value = results[String(matchId)];
    if (!value || value.g1 === "" || value.g2 === "" || value.g1 === null || value.g2 === null) {
      return null;
    }
    return { g1: Number(value.g1), g2: Number(value.g2) };
  }

  function scoreBet(bet, actual) {
    if (!actual || !bet) return { points: 0, exact: false, winner: false, draw: false };
    const exact = bet.g1 === actual.g1 && bet.g2 === actual.g2;
    const betResult = resultCode(bet.g1, bet.g2);
    const actualResult = resultCode(actual.g1, actual.g2);
    const winner = !exact && betResult === actualResult && actualResult !== "D";
    const draw = !exact && betResult === "D" && actualResult === "D";
    return {
      points: exact
        ? data.rules.exactScorePoints || 10
        : winner
          ? data.rules.winnerPoints || 7
          : draw
            ? data.rules.drawPoints || 5
            : 0,
      exact,
      winner,
      draw,
    };
  }

  function participantStats(participant) {
    const byMatch = new Map(participant.bets.map((bet) => [bet.matchId, bet]));
    const completed = data.matches.filter((match) => matchResult(match.id));
    let points = 0;
    let exact = 0;
    let winner = 0;
    let draw = 0;
    let scoredMatches = 0;
    const phaseTotals = {};

    completed.forEach((match) => {
      const bet = byMatch.get(match.id) || { matchId: match.id, g1: 0, g2: 0 };
      const score = scoreBet(bet, matchResult(match.id));
      points += score.points;
      exact += score.exact ? 1 : 0;
      winner += score.winner ? 1 : 0;
      draw += score.draw ? 1 : 0;
      scoredMatches += score.points > 0 ? 1 : 0;
      phaseTotals[match.phase] = (phaseTotals[match.phase] || 0) + score.points;
    });

    const weighted = Object.entries(phaseTotals).reduce((sum, [phase, phasePoints]) => {
      const phaseMatches = data.matches.filter((match) => match.phase === phase).length;
      const max = phaseMatches * (data.rules.maxPerMatch || 10);
      const weight = (data.rules.stageWeights || {})[phase] || 0;
      return sum + (max ? (phasePoints / max) * weight : 0);
    }, 0);

    return { points, weighted, exact, winner, draw, scoredMatches };
  }

  function leaderboardRows() {
    return data.participants
      .map((participant) => ({ participant, stats: participantStats(participant) }))
      .sort((a, b) => {
        if (b.stats.points !== a.stats.points) return b.stats.points - a.stats.points;
        if (b.stats.exact !== a.stats.exact) return b.stats.exact - a.stats.exact;
        if (b.stats.winner !== a.stats.winner) return b.stats.winner - a.stats.winner;
        if (b.stats.draw !== a.stats.draw) return b.stats.draw - a.stats.draw;
        return a.participant.name.localeCompare(b.participant.name, "pt-BR");
      });
  }

  function renderMetrics() {
    const completed = data.matches.filter((match) => matchResult(match.id)).length;
    const rows = leaderboardRows();
    document.getElementById("metricParticipants").textContent = data.participants.length;
    document.getElementById("metricMatches").textContent = data.matches.length;
    document.getElementById("metricCompleted").textContent = completed;
    document.getElementById("metricLeader").textContent = rows[0]?.participant.name || "-";
  }

  function renderLeaderboard() {
    const rows = leaderboardRows();
    if (!rows.length) {
      leaderboardBody.innerHTML = `<tr><td colspan="7" class="empty">Nenhuma aposta importada ainda.</td></tr>`;
      return;
    }

    let previousKey = null;
    let rank = 0;
    leaderboardBody.innerHTML = rows
      .map((row, index) => {
        const key = `${row.stats.points}|${row.stats.exact}|${row.stats.winner}|${row.stats.draw}`;
        if (key !== previousKey) rank = index + 1;
        previousKey = key;
        return `
          <tr>
            <td><span class="rank-badge">${rank}</span></td>
            <td><strong>${escapeHtml(row.participant.name)}</strong></td>
            <td>${row.stats.points}</td>
            <td>${row.stats.exact}</td>
            <td>${row.stats.winner}</td>
            <td>${row.stats.draw}</td>
            <td>${row.stats.scoredMatches}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderResultsGrid() {
    if (!data.matches.length) {
      resultsGrid.innerHTML = `<div class="empty">Nenhum jogo importado ainda.</div>`;
      return;
    }

    resultsGrid.innerHTML = data.matches
      .map((match) => {
        const actual = matchResult(match.id) || { g1: "", g2: "" };
        return `
          <article class="match-card">
            <div class="match-meta">
              <span>#${match.id} · Grupo ${escapeHtml(match.group || "-")}</span>
              <span>${escapeHtml(formatDate(match.date))}</span>
            </div>
            <div class="score-row">
              <strong class="team-right">${escapeHtml(match.team1)}</strong>
              <input class="score-input" type="number" min="0" inputmode="numeric"
                value="${actual.g1}" aria-label="${escapeHtml(match.team1)}"
                data-match="${match.id}" data-side="g1" ${isAdmin ? "" : "disabled"}>
              <span class="versus">x</span>
              <input class="score-input" type="number" min="0" inputmode="numeric"
                value="${actual.g2}" aria-label="${escapeHtml(match.team2)}"
                data-match="${match.id}" data-side="g2" ${isAdmin ? "" : "disabled"}>
              <strong>${escapeHtml(match.team2)}</strong>
            </div>
          </article>
        `;
      })
      .join("");

    resultsGrid.querySelectorAll("input").forEach((input) => {
      input.addEventListener("input", () => {
        if (!isAdmin) return;
        renderMetrics();
        renderLeaderboard();
        renderMatchBetsBoard();
        renderParticipantBets();
      });
    });
  }

  function renderMatchBetsBoard() {
    if (!matchBetsBoard) return;
    if (!data.matches.length) {
      matchBetsBoard.innerHTML = `<div class="empty">Nenhum jogo importado ainda.</div>`;
      return;
    }

    const categories = categorizeMatches();
    matchBetsBoard.innerHTML = categories
      .map((category) => `
        <section class="match-bets-column">
          <div class="match-bets-column-heading">
            <h3>${escapeHtml(category.title)}</h3>
            <span>${category.matches.length}</span>
          </div>
          <div class="match-bets-list">
            ${
              category.matches.length
                ? category.matches.map(renderMatchBetsCard).join("")
                : `<div class="empty compact">${escapeHtml(category.emptyText)}</div>`
            }
          </div>
        </section>
      `)
      .join("");
  }

  function categorizeMatches() {
    const today = startOfLocalDay(new Date());
    const groups = {
      today: [],
      next: [],
      future: [],
      past: [],
    };

    data.matches.forEach((match) => {
      const matchDate = parseLocalDate(match.date);
      if (!matchDate) {
        groups.future.push(match);
        return;
      }
      const dayDelta = Math.round((matchDate - today) / 86400000);
      if (dayDelta === 0) {
        groups.today.push(match);
      } else if (dayDelta > 0 && dayDelta <= 3) {
        groups.next.push(match);
      } else if (dayDelta > 3) {
        groups.future.push(match);
      } else {
        groups.past.push(match);
      }
    });

    const byDateAsc = (a, b) => (a.date || "").localeCompare(b.date || "") || a.id - b.id;
    const byDateDesc = (a, b) => (b.date || "").localeCompare(a.date || "") || a.id - b.id;

    return [
      {
        title: "Jogos do dia",
        emptyText: "Nenhum jogo hoje.",
        matches: groups.today.sort(byDateAsc),
      },
      {
        title: "Próximos 3 dias",
        emptyText: "Nenhum jogo nos próximos 3 dias.",
        matches: groups.next.sort(byDateAsc),
      },
      {
        title: "Jogos futuros",
        emptyText: "Nenhum jogo futuro.",
        matches: groups.future.sort(byDateAsc),
      },
      {
        title: "Jogos passados",
        emptyText: "Nenhum jogo passado.",
        matches: groups.past.sort(byDateDesc),
      },
    ];
  }

  function renderMatchBetsCard(match) {
    const actual = matchResult(match.id);
    const resultLabel = actual ? `${actual.g1} x ${actual.g2}` : "Sem resultado";
    const betsByParticipant = data.participants
      .map((participant) => {
        const bet = participant.bets.find((item) => item.matchId === match.id);
        const scored = scoreBet(bet, actual);
        const pointClass = scored.exact ? "points-exact" : scored.points > 0 ? "points-good" : "";
        return `
          <tr>
            <td>${escapeHtml(participant.name)}</td>
            <td>${bet ? `${bet.g1} x ${bet.g2}` : "-"}</td>
            <td class="${pointClass}">${actual ? scored.points : "-"}</td>
          </tr>
        `;
      })
      .join("");

    return `
      <details class="match-bets-card">
        <summary>
          <span class="match-bets-meta">#${match.id} · Grupo ${escapeHtml(match.group || "-")} · ${escapeHtml(formatDate(match.date))}</span>
          <strong>${escapeHtml(match.team1)} x ${escapeHtml(match.team2)}</strong>
          <span class="match-bets-result">${escapeHtml(resultLabel)}</span>
        </summary>
        <div class="match-bets-details">
          <table class="compact-table">
            <thead>
              <tr>
                <th>Participante</th>
                <th>Palpite</th>
                <th>Pontos</th>
              </tr>
            </thead>
            <tbody>${betsByParticipant}</tbody>
          </table>
        </div>
      </details>
    `;
  }

  function renderParticipantSelect() {
    const selected = participantSelect.value;
    participantSelect.innerHTML = data.participants
      .map((participant) => `<option value="${escapeHtml(participant.id)}">${escapeHtml(participant.name)}</option>`)
      .join("");
    if (selected && data.participants.some((participant) => participant.id === selected)) {
      participantSelect.value = selected;
    }
  }

  function renderParticipantBets() {
    const participant = data.participants.find((item) => item.id === participantSelect.value) || data.participants[0];
    if (!participant) {
      participantBetsBody.innerHTML = `<tr><td colspan="6" class="empty">Nenhum participante importado ainda.</td></tr>`;
      return;
    }

    const bets = new Map(participant.bets.map((bet) => [bet.matchId, bet]));
    participantBetsBody.innerHTML = data.matches
      .map((match) => {
        const bet = bets.get(match.id) || { g1: 0, g2: 0 };
        const actual = matchResult(match.id);
        const scored = scoreBet(bet, actual);
        const pointClass = scored.exact ? "points-exact" : scored.points > 0 ? "points-good" : "";
        return `
          <tr>
            <td>${match.id}</td>
            <td>${escapeHtml(match.group || "-")}</td>
            <td>${escapeHtml(match.team1)} x ${escapeHtml(match.team2)}</td>
            <td>${bet.g1} x ${bet.g2}</td>
            <td>${actual ? `${actual.g1} x ${actual.g2}` : "-"}</td>
            <td class="${pointClass}">${scored.points}</td>
          </tr>
        `;
      })
      .join("");
  }

  function formatDate(value) {
    if (!value) return "";
    const [year, month, day] = value.split("-");
    return `${day}/${month}/${year}`;
  }

  function parseLocalDate(value) {
    if (!value) return null;
    const [year, month, day] = value.split("-").map(Number);
    if (!year || !month || !day) return null;
    return new Date(year, month - 1, day);
  }

  function startOfLocalDay(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate());
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
})();
