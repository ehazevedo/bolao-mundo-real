#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_bets import extract_workbook  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "bolao-data.js"
INPUT_DIR = ROOT / "apostas"
OUTPUT_DIR = ROOT / "outputs"


def load_data():
    text = DATA_FILE.read_text(encoding="utf-8")
    match = re.search(r"window\.BOLAO_DATA\s*=\s*(\{.*\});?\s*$", text, flags=re.S)
    if not match:
        raise SystemExit(f"Não consegui ler {DATA_FILE}.")
    return json.loads(match.group(1))


def score_text(bet):
    if not bet:
        return ""
    g1 = "" if bet.get("g1") is None else bet.get("g1")
    g2 = "" if bet.get("g2") is None else bet.get("g2")
    return f"{g1} x {g2}"


def phase_bucket(match_id):
    if 1 <= match_id <= 72:
        return "Fase de Grupos"
    if 73 <= match_id <= 88:
        return "16 avos"
    if 89 <= match_id <= 96:
        return "Oitavas"
    if 97 <= match_id <= 100:
        return "Quartas"
    if 101 <= match_id <= 102:
        return "Semifinal"
    if match_id == 103:
        return "3º lugar"
    if match_id == 104:
        return "Final"
    return "Outra"


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    data = load_data()
    OUTPUT_DIR.mkdir(exist_ok=True)

    matches = {int(match["id"]): match for match in data.get("matches", [])}
    participants = data.get("participants", [])
    source_files = sorted(path for path in INPUT_DIR.rglob("*.xlsx") if not path.name.startswith("~$"))
    source_file_names = {path.name for path in source_files}

    base_rows = []
    integrity_alerts = []
    participant_bets = {}
    expected_total = max(matches) if matches else 0
    expected_ids = set(range(1, expected_total + 1))

    match_ids = [int(match["id"]) for match in data.get("matches", [])]
    duplicate_match_ids = sorted(id_ for id_, count in Counter(match_ids).items() if count > 1)
    if len(matches) != expected_total:
        integrity_alerts.append({"tipo": "jogos", "detalhe": f"Base tem {len(matches)} jogos, mas o maior ID é {expected_total}."})
    if duplicate_match_ids:
        integrity_alerts.append({"tipo": "jogos", "detalhe": f"IDs de jogos duplicados: {duplicate_match_ids}"})

    for participant in participants:
        bets = {int(bet["matchId"]): bet for bet in participant.get("bets", [])}
        participant_bets[participant["id"]] = bets
        ids = [int(bet["matchId"]) for bet in participant.get("bets", [])]
        missing = sorted(expected_ids - set(ids))
        duplicates = sorted(id_ for id_, count in Counter(ids).items() if count > 1)
        blanks = sorted(
            int(bet["matchId"])
            for bet in participant.get("bets", [])
            if bet.get("g1") is None or bet.get("g2") is None
        )
        if len(ids) != expected_total:
            integrity_alerts.append({"tipo": "participante", "detalhe": f"{participant['name']} tem {len(ids)} palpites."})
        if missing:
            integrity_alerts.append({"tipo": "participante", "detalhe": f"{participant['name']} sem palpites: {missing}"})
        if duplicates:
            integrity_alerts.append({"tipo": "participante", "detalhe": f"{participant['name']} com palpites duplicados: {duplicates}"})
        if blanks:
            integrity_alerts.append({"tipo": "participante", "detalhe": f"{participant['name']} com placares vazios: {blanks}"})

        for match_id in range(1, expected_total + 1):
            match = matches.get(match_id, {})
            bet = bets.get(match_id)
            base_rows.append(
                {
                    "participante": participant["name"],
                    "id_participante": participant["id"],
                    "jogo": match_id,
                    "fase": phase_bucket(match_id),
                    "data": match.get("date", ""),
                    "selecao_1": match.get("team1", ""),
                    "palpite_1": "" if not bet or bet.get("g1") is None else bet.get("g1"),
                    "palpite_2": "" if not bet or bet.get("g2") is None else bet.get("g2"),
                    "selecao_2": match.get("team2", ""),
                    "status": "OK" if bet and bet.get("g1") is not None and bet.get("g2") is not None else "ALERTA",
                }
            )

    source_rows = []
    source_errors = []
    extracted_files = []
    for path in source_files:
        extracted = extract_workbook(path)
        participant = extracted["participant"]
        extracted_files.append(
            {
                "arquivo": str(path.relative_to(ROOT)),
                "participante_detectado": participant["name"],
                "id_participante": participant["id"],
                "apostas": len(participant.get("bets", [])),
                "primeiro_jogo": min((bet["matchId"] for bet in participant.get("bets", [])), default=""),
                "ultimo_jogo": max((bet["matchId"] for bet in participant.get("bets", [])), default=""),
            }
        )
        for bet in participant.get("bets", []):
            match_id = int(bet["matchId"])
            base_bet = participant_bets.get(participant["id"], {}).get(match_id)
            match = matches.get(match_id, {})
            ok = bool(base_bet) and base_bet.get("g1") == bet.get("g1") and base_bet.get("g2") == bet.get("g2")
            if not ok:
                source_errors.append(
                    {
                        "arquivo": str(path.relative_to(ROOT)),
                        "participante": participant["name"],
                        "jogo": match_id,
                        "planilha": score_text(bet),
                        "site": score_text(base_bet),
                    }
                )
            source_rows.append(
                {
                    "arquivo": str(path.relative_to(ROOT)),
                    "participante_detectado": participant["name"],
                    "id_participante": participant["id"],
                    "jogo": match_id,
                    "fase": phase_bucket(match_id),
                    "data": match.get("date", ""),
                    "selecao_1": match.get("team1", ""),
                    "palpite_1_planilha": "" if bet.get("g1") is None else bet.get("g1"),
                    "palpite_2_planilha": "" if bet.get("g2") is None else bet.get("g2"),
                    "selecao_2": match.get("team2", ""),
                    "palpite_site": score_text(base_bet),
                    "status": "OK" if ok else "DIVERGENTE",
                }
            )

    expected_files = []
    for participant in participants:
        for file_name in [item.strip() for item in str(participant.get("file", "")).split(";") if item.strip()]:
            expected_files.append({"participante": participant["name"], "arquivo": file_name, "presente": file_name in source_file_names})

    missing_source_files = [row for row in expected_files if not row["presente"]]
    if source_errors:
        integrity_alerts.append({"tipo": "planilha", "detalhe": f"{len(source_errors)} divergência(s) entre Excel e base."})
    if missing_source_files:
        integrity_alerts.append(
            {
                "tipo": "fonte",
                "detalhe": f"{len(missing_source_files)} arquivo(s) referenciado(s) não estão na pasta atual; normalmente são as planilhas da fase de grupos.",
            }
        )

    summary_rows = []
    for participant in participants:
        bets = participant_bets[participant["id"]]
        for label, start, end in [
            ("Fase de Grupos", 1, 72),
            ("16 avos", 73, 88),
            ("Oitavas", 89, 96),
            ("Quartas", 97, 100),
            ("Semifinal", 101, 102),
            ("3º lugar", 103, 103),
            ("Final", 104, 104),
        ]:
            if start > expected_total:
                continue
            end = min(end, expected_total)
            phase_bets = [bets.get(match_id) for match_id in range(start, end + 1)]
            summary_rows.append(
                {
                    "participante": participant["name"],
                    "fase": label,
                    "apostas_esperadas": end - start + 1,
                    "apostas_presentes": sum(1 for bet in phase_bets if bet),
                    "placares_completos": sum(1 for bet in phase_bets if bet and bet.get("g1") is not None and bet.get("g2") is not None),
                }
            )

    write_csv(
        OUTPUT_DIR / "auditoria-base-completa-2026-07-11.csv",
        base_rows,
        ["participante", "id_participante", "jogo", "fase", "data", "selecao_1", "palpite_1", "palpite_2", "selecao_2", "status"],
    )
    write_csv(
        OUTPUT_DIR / "auditoria-planilhas-disponiveis-2026-07-11.csv",
        source_rows,
        [
            "arquivo",
            "participante_detectado",
            "id_participante",
            "jogo",
            "fase",
            "data",
            "selecao_1",
            "palpite_1_planilha",
            "palpite_2_planilha",
            "selecao_2",
            "palpite_site",
            "status",
        ],
    )
    write_csv(
        OUTPUT_DIR / "auditoria-resumo-2026-07-11.csv",
        summary_rows,
        ["participante", "fase", "apostas_esperadas", "apostas_presentes", "placares_completos"],
    )
    write_csv(
        OUTPUT_DIR / "auditoria-arquivos-fonte-2026-07-11.csv",
        expected_files,
        ["participante", "arquivo", "presente"],
    )
    write_csv(
        OUTPUT_DIR / "auditoria-alertas-2026-07-11.csv",
        integrity_alerts or [{"tipo": "OK", "detalhe": "Nenhum alerta encontrado."}],
        ["tipo", "detalhe"],
    )

    print(f"Participantes: {len(participants)}")
    print(f"Jogos: {len(matches)}")
    print(f"Palpites na base: {len(base_rows)}")
    print(f"Palpites conferidos em planilhas disponíveis: {len(source_rows)}")
    print(f"Divergências Excel x base: {len(source_errors)}")
    print(f"Arquivos fonte ausentes: {len(missing_source_files)}")
    print(f"Alertas: {len(integrity_alerts)}")


if __name__ == "__main__":
    main()
