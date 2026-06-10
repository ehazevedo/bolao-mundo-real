# Bolão Mundo Real

Dashboard estático para acompanhar palpites, resultados e classificação do bolão.

Esta pasta foi criada para publicar o Bolão Mundo Real separado dos outros bolões. Para usar no GitHub Pages, publique o conteúdo desta pasta em um repositório/página própria.

## Regras

O regulamento completo está disponível na aba **Regras** do dashboard.

Resumo:

- Participação: R$ 50,00 por pessoa.
- Primeira Fase: 40% da pontuação total, com envio até 09/06/2026 para eduardohenriqueazevedo@gmail.com.
- Mata-Mata: 50% da pontuação total, com envio até 28/06/2026 antes do primeiro jogo eliminatório.
- Campeão da Copa: 10% da pontuação total, indicado junto com o Excel da segunda fase.
- Placar exato: 10 pontos.
- Acertou o vencedor: 7 pontos.
- Empate sem placar exato: 5 pontos.
- Errou o vencedor ou não palpitou: 0 ponto.

## Atualizar palpites

Coloque os arquivos Excel recebidos na pasta `apostas/` e rode:

```bash
/Users/ehazevedo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_bets.py --input apostas --output data/bolao-data.js
```

## Atualizar resultados

Os resultados oficiais são lidos de uma Google Sheet configurada em `data/config.js`.

Para este bolão, crie uma planilha própria e coloque o ID dela em `googleSheetId`.

A planilha deve estar compartilhada como **qualquer pessoa com o link pode visualizar** e precisa ter as colunas:

| matchId | g1 | g2 |
| --- | --- | --- |
| 1 | 2 | 0 |
| 2 | 1 | 1 |

Para atualizar pelo celular, edite os placares na Google Sheet. O dashboard público recalcula quando a página é aberta ou recarregada.

`data/results.js` fica como fallback caso a planilha esteja indisponível.

No GitHub Pages, visitantes veem o dashboard em modo somente leitura. Os botões administrativos aparecem apenas em `localhost`.

## Publicar no GitHub Pages

1. Crie um repositório no GitHub.
2. Faça commit dos arquivos do dashboard.
3. Envie para o GitHub.
4. Em **Settings > Pages**, selecione **Deploy from a branch**, branch `main`, pasta `/root`.
5. O GitHub Pages publicará o link do dashboard.

Não publique os Excel brutos da pasta `apostas/`; eles são ignorados pelo Git. O site usa apenas os arquivos consolidados em `data/`.
