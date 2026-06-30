import fs from "node:fs/promises";
import vm from "node:vm";

const dataCode = await fs.readFile("/Users/tvs/Documents/Bolão Mundo Real/data/bolao-data.js", "utf8");
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(dataCode, sandbox);
const data = sandbox.window.BOLAO_DATA;

const sheetText = await fs.readFile("/private/tmp/bolao_sheet_results.txt", "utf8");
const jsonText = sheetText.replace(/^.*?setResponse\(/s, "").replace(/\);\s*$/s, "");
const payload = JSON.parse(jsonText);

function normalizeHeader(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]/g, "")
    .toLowerCase();
}

const headers = payload.table.cols.map((col, index) => normalizeHeader(col.label || col.id || `col${index}`));
const matchIdIndex = headers.findIndex((header) => ["matchid", "jogo", "match", "id"].includes(header));
const g1Index = headers.findIndex((header) => ["g1", "placar1", "gols1", "time1", "casa"].includes(header));
const g2Index = headers.findIndex((header) => ["g2", "placar2", "gols2", "time2", "fora"].includes(header));

const results = new Map();
for (const row of payload.table.rows || []) {
  const cells = row.c || [];
  const id = cells[matchIdIndex]?.v;
  const g1 = cells[g1Index]?.v;
  const g2 = cells[g2Index]?.v;
  if (Number.isInteger(id) && Number.isInteger(g1) && Number.isInteger(g2)) {
    results.set(id, { g1, g2 });
  }
}

function emptyStats(team, group) {
  return { team, group, pts: 0, pj: 0, v: 0, e: 0, d: 0, gp: 0, gc: 0, sg: 0 };
}

const groups = new Map();
for (const match of data.matches) {
  if (!groups.has(match.group)) groups.set(match.group, new Map());
  const table = groups.get(match.group);
  if (!table.has(match.team1)) table.set(match.team1, emptyStats(match.team1, match.group));
  if (!table.has(match.team2)) table.set(match.team2, emptyStats(match.team2, match.group));
  const score = results.get(match.id);
  if (!score) continue;
  const a = table.get(match.team1);
  const b = table.get(match.team2);
  a.pj += 1;
  b.pj += 1;
  a.gp += score.g1;
  a.gc += score.g2;
  b.gp += score.g2;
  b.gc += score.g1;
  a.sg = a.gp - a.gc;
  b.sg = b.gp - b.gc;
  if (score.g1 > score.g2) {
    a.pts += 3;
    a.v += 1;
    b.d += 1;
  } else if (score.g1 < score.g2) {
    b.pts += 3;
    b.v += 1;
    a.d += 1;
  } else {
    a.pts += 1;
    b.pts += 1;
    a.e += 1;
    b.e += 1;
  }
}

function rankTeams(list) {
  return [...list].sort((a, b) =>
    b.pts - a.pts ||
    b.sg - a.sg ||
    b.gp - a.gp ||
    a.gc - b.gc ||
    a.team.localeCompare(b.team, "pt-BR"),
  );
}

const standings = {};
for (const [group, table] of groups) {
  standings[group] = rankTeams(table.values());
}

const third = Object.values(standings)
  .map((rows) => rows[2])
  .filter(Boolean);
const bestThirds = rankTeams(third).slice(0, 8);

const output = {
  completed: results.size,
  standings,
  qualifiers: Object.fromEntries(
    Object.entries(standings).map(([group, rows]) => [
      group,
      {
        first: rows[0]?.team || "",
        second: rows[1]?.team || "",
        third: rows[2]?.team || "",
        thirdQualified: bestThirds.some((item) => item.group === group),
      },
    ]),
  ),
  bestThirds,
  yesterdayResults: data.matches
    .filter((match) => match.date === "2026-06-26")
    .map((match) => ({ ...match, result: results.get(match.id) || null })),
};

await fs.writeFile("/private/tmp/bolao_classificados.json", JSON.stringify(output, null, 2), "utf8");
console.log(JSON.stringify({
  completed: output.completed,
  bestThirdGroups: bestThirds.map((team) => team.group).join(""),
  yesterdayResults: output.yesterdayResults,
  qualifiers: output.qualifiers,
}, null, 2));
