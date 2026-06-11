# Bolão Mundo Real

Dashboard estático para acompanhar palpites, resultados e classificação do bolão.

Esta pasta foi criada para publicar o Bolão Mundo Real separado dos outros bolões. Para usar no GitHub Pages, publique o conteúdo desta pasta em um repositório/página própria.

## Regras

O regulamento completo está disponível na aba **Regras** do dashboard.

Resumo:

- Participação: R$ 50,00 por pessoa.
- Total com 8 participantes: R$ 400,00.
- Premiação: 1º lugar R$ 240,00, 2º lugar R$ 120,00 e 3º lugar R$ 40,00.
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

A planilha usada atualmente é:

- ID: `15I2_YnnCAKrU2UleQjE3Q40tGK87FSYL`
- Aba/GID: `0`
- URL: `https://docs.google.com/spreadsheets/d/15I2_YnnCAKrU2UleQjE3Q40tGK87FSYL/edit`

A planilha deve estar compartilhada como **qualquer pessoa com o link pode visualizar** e precisa ter as colunas:

| matchId | g1 | g2 |
| --- | --- | --- |
| 1 | 2 | 0 |
| 2 | 1 | 1 |

Para atualizar pelo celular, edite os placares na Google Sheet. O dashboard público recalcula quando a página é aberta ou recarregada.

`data/results.js` fica como fallback caso a planilha esteja indisponível.

No GitHub Pages, visitantes veem o dashboard em modo somente leitura. Os botões administrativos aparecem apenas em `localhost`.

## Fuso horário

As datas da aba **Jogos** usam o fuso `America/Sao_Paulo` para separar:

- Jogos do dia.
- Próximos 3 dias.
- Jogos futuros.
- Jogos passados.

## Cache

O `index.html` carrega CSS, dados, configuração e JavaScript com um cache-buster automático por abertura de página. Assim, depois de publicar no GitHub Pages, o navegador tende a buscar a versão mais recente dos arquivos auxiliares sem precisar editar `?v=` manualmente.

## Checklist de atualização

1. Coloque novas planilhas de apostas em `apostas/`.
2. Rode a importação:

```bash
/Users/ehazevedo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_bets.py --input apostas --output data/bolao-data.js
```

3. Verifique se a saída mostra o número esperado de participantes e 72 jogos.
4. Rode as validações:

```bash
/Users/ehazevedo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile scripts/import_bets.py
/Users/ehazevedo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check app.js
```

5. Faça commit dos arquivos alterados.
6. Envie para `main` e atualize o branch do GitHub Pages:

```bash
git push origin main
git push origin main:gh-pages
```

7. Abra `https://ehazevedo.github.io/bolao-mundo-real/` e confirme participantes, placares e aba **Jogos**.

## Publicar no GitHub Pages

1. Crie um repositório no GitHub.
2. Faça commit dos arquivos do dashboard.
3. Envie para o GitHub.
4. Em **Settings > Pages**, selecione **Deploy from a branch**, branch `main`, pasta `/root`.
5. O GitHub Pages publicará o link do dashboard.

Não publique os Excel brutos da pasta `apostas/`; eles são ignorados pelo Git. O site usa apenas os arquivos consolidados em `data/`.
