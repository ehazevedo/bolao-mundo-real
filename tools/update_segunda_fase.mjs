import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "/Users/tvs/Downloads/SEU_NOME_resultados_playoffs_copa_2026_oficial_fifa.xlsx";
const outputDir = "/Users/tvs/Documents/Bolão Mundo Real/outputs/segunda-fase";
const outputPath = path.join(outputDir, "SEU_NOME_resultados_playoffs_copa_2026_oficial_fifa_atualizada_2026-06-27.xlsx");

await fs.mkdir(outputDir, { recursive: true });

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const playoffs = workbook.worksheets.getItem("Resultados_Playoffs");
const bracket = workbook.worksheets.getItem("Chaveamento");
const sources = workbook.worksheets.getItem("Fontes");

playoffs.getRange("A2:P2").values = [[
  "Atualizada com os placares de 2026-06-26. Preencha as células em azul claro. Vagas dos Grupos J/K/L e alguns melhores terceiros dependem dos jogos de 2026-06-27.",
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
]];

playoffs.getRange("F14").values = [["Belgium"]];
playoffs.getRange("F16").values = [["Spain"]];
playoffs.getRange("I18").values = [["Cape Verde"]];
playoffs.getRange("I20").values = [["Egypt"]];

playoffs.getRange("P9:P10").values = [
  ["Grupo I definido em 2026-06-26"],
  ["Grupo I definido em 2026-06-26"],
];
playoffs.getRange("P14").values = [["Grupo G definido antes de 2026-06-27"]];
playoffs.getRange("P16").values = [["Grupo H definido em 2026-06-26"]];
playoffs.getRange("P18").values = [["Grupo H definido em 2026-06-26"]];
playoffs.getRange("P20").values = [["Grupo G definido antes de 2026-06-27"]];
playoffs.getRange("P12:P13").values = [
  ["A definir após jogos de 2026-06-27"],
  ["Melhor terceiro ainda depende dos jogos de 2026-06-27"],
];
playoffs.getRange("P15").values = [["A definir após jogos de 2026-06-27"]];
playoffs.getRange("P17").values = [["Melhor terceiro ainda depende dos jogos de 2026-06-27"]];
playoffs.getRange("P19").values = [["A definir após jogos de 2026-06-27"]];

playoffs.getRange("A38:P38").merge();
playoffs.getRange("A38").values = [[
  "CAMPEÃO DA COPA (10% da pontuação total): escreva aqui o campeão escolhido para a segunda fase.",
]];
playoffs.getRange("A39:P39").merge();
playoffs.getRange("A39").values = [["Campeão escolhido: ______________________________"]];
playoffs.getRange("A38:P39").format = {
  fill: "#FFF2CC",
  font: { bold: true, color: "#173B57" },
  horizontalAlignment: "center",
  wrapText: false,
  borders: { preset: "outside", style: "thin", color: "#C9A227" },
};
playoffs.getRange("A38:P38").format.rowHeight = 24;
playoffs.getRange("A39:P39").format.rowHeight = 30;
playoffs.getRange("A38").format.font = { bold: true, color: "#173B57", fontSize: 14 };
playoffs.getRange("A39").format.font = { bold: true, color: "#000000", fontSize: 16 };

bracket.getRange("M12:N12").merge();
bracket.getRange("M12").values = [["Campeão da Copa"]];
bracket.getRange("M13:N13").merge();
bracket.getRange("M13").values = [["Palpite vale 10% da pontuação total"]];
bracket.getRange("M12:N13").format = {
  fill: "#FFF2CC",
  font: { bold: true, color: "#173B57" },
  horizontalAlignment: "center",
  wrapText: true,
  borders: { preset: "outside", style: "thin", color: "#C9A227" },
};

sources.getRange("A5:D5").values = [[
  "Google Sheet do bolão",
  "Configurada no dashboard local",
  "Placares",
  "Placares de 2026-06-26 usados para atualizar Grupos H e I; J/K/L seguem pendentes em 2026-06-27.",
]];

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  maxChars: 12000,
});

const check = await workbook.inspect({
  kind: "region,formula",
  sheetId: "Resultados_Playoffs",
  range: "A1:P39",
  tableMaxRows: 39,
  tableMaxCols: 16,
  tableMaxCellChars: 120,
  maxChars: 26000,
});

await fs.writeFile(path.join(outputDir, "qa_formula_errors.ndjson"), formulaErrors.ndjson, "utf8");
await fs.writeFile(path.join(outputDir, "qa_resultados_playoffs.ndjson"), check.ndjson, "utf8");

for (const sheetName of ["Resultados_Playoffs", "Chaveamento"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(outputDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

console.log(JSON.stringify({ outputPath, formulaErrors: formulaErrors.ndjson.trim() || "none" }, null, 2));
