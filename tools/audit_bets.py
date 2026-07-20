#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_bets import extract_workbook  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "bolao-data.js"
RESULTS_FILE = ROOT / "data" / "results.js"
INPUT_DIR = ROOT / "apostas"
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_STAMP = date.today().isoformat()


def load_data():
    text = DATA_FILE.read_text(encoding="utf-8")
    match = re.search(r"window\.BOLAO_DATA\s*=\s*(\{.*\});?\s*$", text, flags=re.S)
    if not match:
        raise SystemExit(f"Não consegui ler {DATA_FILE}.")
    return json.loads(match.group(1))


def load_results():
    text = RESULTS_FILE.read_text(encoding="utf-8")
    match = re.search(r"window\.BOLAO_RESULTS\s*=\s*(\{.*\});?\s*$", text, flags=re.S)
    if not match:
        raise SystemExit(f"Não consegui ler {RESULTS_FILE}.")
    return {int(key): value for key, value in json.loads(match.group(1)).items() if str(key).isdigit()}


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


def stage_key(match_id):
    return "Fase de Grupos" if 1 <= match_id <= 72 else "Mata-Mata"


def normalized_text(value):
    return (
        unicodedata.normalize("NFKD", str(value or ""))
        .encode("ascii", "ignore")
        .decode("ascii")
        .replace("'", "")
        .replace(".", "")
        .replace(" ", "")
        .lower()
    )


def normalize_team(value):
    aliases = {
        "africadosul": "southafrica",
        "southafrica": "southafrica",
        "canada": "canada",
        "brasil": "brazil",
        "brazil": "brazil",
        "japao": "japan",
        "japan": "japan",
        "alemanha": "germany",
        "germany": "germany",
        "paraguai": "paraguay",
        "paraguay": "paraguay",
        "holanda": "netherlands",
        "paisesbaixos": "netherlands",
        "netherlands": "netherlands",
        "marrocos": "morocco",
        "morocco": "morocco",
        "costadomarfim": "ivorycoast",
        "cotedivoire": "ivorycoast",
        "noruega": "norway",
        "norway": "norway",
        "franca": "france",
        "france": "france",
        "suecia": "sweden",
        "sweden": "sweden",
        "mexico": "mexico",
        "equador": "ecuador",
        "ecuador": "ecuador",
        "inglaterra": "england",
        "england": "england",
        "congo": "drcongo",
        "rdcongo": "drcongo",
        "belgica": "belgium",
        "belgium": "belgium",
        "estadosunidos": "usa",
        "usa": "usa",
        "bosnia": "bosnia",
        "bosniaeherzegovina": "bosnia",
        "espanha": "spain",
        "spain": "spain",
        "austria": "austria",
        "portugal": "portugal",
        "croacia": "croatia",
        "croatia": "croatia",
        "suica": "switzerland",
        "switzerland": "switzerland",
        "argelia": "algeria",
        "algeria": "algeria",
        "australia": "australia",
        "egito": "egypt",
        "egypt": "egypt",
        "argentina": "argentina",
        "caboverde": "capeverde",
        "capeverde": "capeverde",
        "colombia": "colombia",
        "gana": "ghana",
        "ghana": "ghana",
    }
    normalized = normalized_text(value)
    return aliases.get(normalized, normalized)


def same_team_order(source_match, base_match):
    if not source_match or not base_match:
        return False
    return (
        normalize_team(source_match.get("team1")) == normalize_team(base_match.get("team1"))
        and normalize_team(source_match.get("team2")) == normalize_team(base_match.get("team2"))
    )


def result_code(g1, g2):
    if g1 > g2:
        return "H"
    if g1 < g2:
        return "A"
    return "D"


def score_bet(bet, actual, rules):
    if not bet or not actual or bet.get("g1") is None or bet.get("g2") is None:
        return {"points": 0, "exact": False, "winner": False, "draw": False}
    bet_g1 = int(bet["g1"])
    bet_g2 = int(bet["g2"])
    actual_g1 = int(actual["g1"])
    actual_g2 = int(actual["g2"])
    exact = bet_g1 == actual_g1 and bet_g2 == actual_g2
    bet_result = result_code(bet_g1, bet_g2)
    actual_result = result_code(actual_g1, actual_g2)
    winner = not exact and bet_result == actual_result and actual_result != "D"
    draw = not exact and bet_result == "D" and actual_result == "D"
    return {
        "points": rules.get("exactScorePoints", 10)
        if exact
        else rules.get("winnerPoints", 7)
        if winner
        else rules.get("drawPoints", 5)
        if draw
        else rules.get("wrongPoints", 0),
        "exact": exact,
        "winner": winner,
        "draw": draw,
    }


def champion_bonus(participant, rules):
    pick = participant.get("champion", "")
    actual = rules.get("actualChampion", "")
    if not pick or not actual:
        return 0
    return rules.get("championBonusPoints", 10) if normalize_team(pick) == normalize_team(actual) else 0


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    data = load_data()
    results = load_results()
    rules = data.get("rules", {})
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
    order_errors = []
    extracted_files = []
    for path in source_files:
        extracted = extract_workbook(path)
        participant = extracted["participant"]
        source_matches = {int(match["id"]): match for match in extracted.get("matches", [])}
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
            source_match = source_matches.get(match_id)
            order_ok = same_team_order(source_match, match)
            ok = bool(base_bet) and base_bet.get("g1") == bet.get("g1") and base_bet.get("g2") == bet.get("g2")
            if not order_ok:
                order_errors.append(
                    {
                        "arquivo": str(path.relative_to(ROOT)),
                        "participante": participant["name"],
                        "jogo": match_id,
                        "planilha": f"{source_match.get('team1', '')} x {source_match.get('team2', '')}" if source_match else "",
                        "base": f"{match.get('team1', '')} x {match.get('team2', '')}",
                    }
                )
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
                    "selecao_1_planilha": source_match.get("team1", "") if source_match else "",
                    "selecao_2_planilha": source_match.get("team2", "") if source_match else "",
                    "ordem_times": "OK" if order_ok else "DIVERGENTE",
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
    if order_errors:
        integrity_alerts.append({"tipo": "ordem_times", "detalhe": f"{len(order_errors)} jogo(s) com ordem de times divergente entre Excel e base."})
    if missing_source_files:
        integrity_alerts.append(
            {
                "tipo": "fonte",
                "detalhe": f"{len(missing_source_files)} arquivo(s) referenciado(s) não estão na pasta atual; normalmente são as planilhas da fase de grupos.",
            }
        )

    summary_rows = []
    score_rows = []
    score_detail_rows = []
    for participant in participants:
        bets = participant_bets[participant["id"]]
        stage_points = {"Fase de Grupos": 0, "Mata-Mata": 0}
        exact_total = 0
        winner_total = 0
        draw_total = 0
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
        for match_id in range(1, expected_total + 1):
            bet = bets.get(match_id)
            actual = results.get(match_id)
            scored = score_bet(bet, actual, rules)
            stage = stage_key(match_id)
            stage_points[stage] += scored["points"]
            exact_total += 1 if scored["exact"] else 0
            winner_total += 1 if scored["winner"] else 0
            draw_total += 1 if scored["draw"] else 0
            match = matches.get(match_id, {})
            score_detail_rows.append(
                {
                    "participante": participant["name"],
                    "jogo": match_id,
                    "fase": phase_bucket(match_id),
                    "selecao_1": match.get("team1", ""),
                    "palpite": score_text(bet),
                    "resultado": score_text(actual),
                    "selecao_2": match.get("team2", ""),
                    "pontos": scored["points"] if actual else "",
                    "tipo": "placar exato"
                    if scored["exact"]
                    else "vencedor"
                    if scored["winner"]
                    else "empate"
                    if scored["draw"]
                    else "erro/sem resultado",
                }
            )
        group_max = rules.get("stageMaxPoints", {}).get("Fase de Grupos", 720)
        knockout_max = rules.get("stageMaxPoints", {}).get("Mata-Mata", 320)
        group_weight = rules.get("stageWeights", {}).get("Fase de Grupos", 40)
        knockout_weight = rules.get("stageWeights", {}).get("Mata-Mata", 50)
        group_weighted = (stage_points["Fase de Grupos"] / group_max) * group_weight if group_max else 0
        knockout_weighted = (stage_points["Mata-Mata"] / knockout_max) * knockout_weight if knockout_max else 0
        champion_points = champion_bonus(participant, rules)
        total_weighted = group_weighted + knockout_weighted + champion_points
        score_rows.append(
            {
                "participante": participant["name"],
                "pontos_primeira_fase": stage_points["Fase de Grupos"],
                "pontos_mata_mata": stage_points["Mata-Mata"],
                "nota_primeira_fase": round(group_weighted, 4),
                "nota_mata_mata": round(knockout_weighted, 4),
                "palpite_campeao": participant.get("champion", ""),
                "campeao_oficial": rules.get("actualChampion", ""),
                "bonus_campeao": champion_points,
                "nota_final": round(total_weighted, 4),
                "placares_exatos": exact_total,
                "vencedores": winner_total,
                "empates": draw_total,
            }
        )

    write_csv(
        OUTPUT_DIR / f"auditoria-base-completa-{OUTPUT_STAMP}.csv",
        base_rows,
        ["participante", "id_participante", "jogo", "fase", "data", "selecao_1", "palpite_1", "palpite_2", "selecao_2", "status"],
    )
    write_csv(
        OUTPUT_DIR / f"auditoria-planilhas-disponiveis-{OUTPUT_STAMP}.csv",
        source_rows,
        [
            "arquivo",
            "participante_detectado",
            "id_participante",
            "jogo",
            "fase",
            "data",
            "selecao_1_planilha",
            "selecao_2_planilha",
            "ordem_times",
            "selecao_1",
            "palpite_1_planilha",
            "palpite_2_planilha",
            "selecao_2",
            "palpite_site",
            "status",
        ],
    )
    write_csv(
        OUTPUT_DIR / f"auditoria-resumo-{OUTPUT_STAMP}.csv",
        summary_rows,
        ["participante", "fase", "apostas_esperadas", "apostas_presentes", "placares_completos"],
    )
    write_csv(
        OUTPUT_DIR / f"auditoria-arquivos-fonte-{OUTPUT_STAMP}.csv",
        expected_files,
        ["participante", "arquivo", "presente"],
    )
    write_csv(
        OUTPUT_DIR / f"auditoria-alertas-{OUTPUT_STAMP}.csv",
        integrity_alerts or [{"tipo": "OK", "detalhe": "Nenhum alerta encontrado."}],
        ["tipo", "detalhe"],
    )
    write_csv(
        OUTPUT_DIR / f"auditoria-pontuacoes-finais-{OUTPUT_STAMP}.csv",
        sorted(score_rows, key=lambda row: (-row["nota_final"], -row["placares_exatos"], row["participante"])),
        [
            "participante",
            "pontos_primeira_fase",
            "pontos_mata_mata",
            "nota_primeira_fase",
            "nota_mata_mata",
            "palpite_campeao",
            "campeao_oficial",
            "bonus_campeao",
            "nota_final",
            "placares_exatos",
            "vencedores",
            "empates",
        ],
    )
    write_csv(
        OUTPUT_DIR / f"auditoria-pontuacoes-detalhe-{OUTPUT_STAMP}.csv",
        score_detail_rows,
        ["participante", "jogo", "fase", "selecao_1", "palpite", "resultado", "selecao_2", "pontos", "tipo"],
    )

    print(f"Participantes: {len(participants)}")
    print(f"Jogos: {len(matches)}")
    print(f"Palpites na base: {len(base_rows)}")
    print(f"Palpites conferidos em planilhas disponíveis: {len(source_rows)}")
    print(f"Divergências Excel x base: {len(source_errors)}")
    print(f"Divergências de ordem dos times: {len(order_errors)}")
    print(f"Arquivos fonte ausentes: {len(missing_source_files)}")
    print(f"Alertas: {len(integrity_alerts)}")


if __name__ == "__main__":
    main()
