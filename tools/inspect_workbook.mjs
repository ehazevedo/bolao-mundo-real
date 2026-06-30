import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "/Users/tvs/Downloads/SEU_NOME_resultados_playoffs_copa_2026_oficial_fifa.xlsx";
const outputDir = "/Users/tvs/Documents/Bolão Mundo Real/outputs/segunda-fase-inspect";

await fs.mkdir(outputDir, { recursive: true });

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const overview = await workbook.inspect({
  kind: "workbook,sheet,table,region",
  tableMaxRows: 12,
  tableMaxCols: 12,
  tableMaxCellChars: 80,
  maxChars: 18000,
});

await fs.writeFile(path.join(outputDir, "overview.ndjson"), overview.ndjson, "utf8");

const sheets = JSON.parse(
  `[${(await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 8000 })).ndjson
    .trim()
    .split("\n")
    .filter(Boolean)
    .join(",")}]`,
);

for (const sheet of sheets) {
  const sheetName = sheet.name;
  const safeName = sheetName.replace(/[^a-z0-9_-]+/gi, "_");
  const table = await workbook.inspect({
    kind: "region,formula,computedStyle",
    sheetId: sheetName,
    range: "A1:Z80",
    tableMaxRows: 80,
    tableMaxCols: 26,
    tableMaxCellChars: 100,
    maxChars: 26000,
    options: { maxResults: 120 },
  });
  await fs.writeFile(path.join(outputDir, `${safeName}.ndjson`), table.ndjson, "utf8");

  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(path.join(outputDir, `${safeName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

console.log(JSON.stringify({ outputDir, sheets: sheets.map((sheet) => sheet.name) }, null, 2));
