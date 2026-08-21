# Console GG

Retro arcade Python da terminale con menu compatto a gruppi, dieci giochi e
salvataggio statistiche locale.

## Avvio

Menu principale:

```powershell
python main.py
```

Il catalogo raggruppa i giochi in quattro sezioni:

- `ROMPICAPO`: 2048, Wordle, Campo Minato
- `TAVOLO`: Blackjack, Tris, Forza 4, Battaglia Navale
- `ARCADE`: Snake, Block Dropper
- `AVVENTURA`: Dungeon

## Giochi E Controlli

- `2048`: `W/A/S/D` o frecce per muovere, `Q` per uscire.
- `Wordle`: lettere + `INVIO`, `Q` per uscire.
- `Campo Minato`: su terminali realtime usa `W/A/S/D` o frecce, `SPAZIO`
  per aprire, `F` bandiera, `R` ricomincia, `Q` esce. In fallback usa
  coordinate come `B4`, `F B4`, `R`, `Q`.
- `Blackjack`: scegli la puntata, poi `C` carta, `S` sto, `Q` esce.
- `Tris`: scegli una casella da `1` a `9`, `Q` esce. Vittorie, sconfitte e
  pareggi vengono salvati solo a partita completata.
- `Forza 4`: scegli una colonna da `1` a `7`, `Q` esce. Vittorie,
  sconfitte e pareggi vengono salvati solo a partita completata.
- `Battaglia Navale`: su terminali realtime usa `W/A/S/D` o frecce,
  `SPAZIO` per sparare, `R` cambia flotta, `Q` esce. In fallback usa
  coordinate come `C7`, poi `INVIO`.
- `Snake`: `W/A/S/D` o frecce, `Q` esce.
- `Block Dropper`: `A/D` muovono, `W` ruota, `S` scende, `SPAZIO` hard drop,
  `P` pausa, `Q` esce.
- `Dungeon`: `W/A/S/D` o frecce per muoversi; il fallback testuale mostra i
  comandi disponibili in schermata; `Q` esce.

## Realtime E Fallback

I giochi che supportano input realtime usano i tasti singoli quando il
backend terminale e disponibile. Quando non lo e, passano automaticamente a
un fallback a riga di comando:

- `Campo Minato`
- `Battaglia Navale`
- `Snake`
- `Block Dropper`
- `Dungeon`

## Statistiche

Le statistiche vengono salvate in `console_gg_stats.json`, creato nella
directory da cui avvii il programma.

Puoi scegliere un path diverso con:

```powershell
$env:CONSOLE_GG_STATS_PATH="C:\console-gg-data\console_gg_stats.json"
```

Metriche principali mostrate nel menu `RECORD`:

- `2048`: `best_score`
- `Wordle`: `best_streak`
- `Campo Minato`: `best_time`
- `Blackjack`: `bankroll`
- `Tris`: `wins`
- `Forza 4`: `wins`
- `Battaglia Navale`: `fewest_shots`
- `Snake`: `best_score`
- `Block Dropper`: `best_score`
- `Dungeon`: `best_score`

## Colori

Per disattivare i colori ANSI:

```powershell
$env:NO_COLOR=1
```

## Installazione Web Su VM Locale

Per usare Console GG come cabinato dal browser, clona la repo nella VM e lancia
un solo installer dalla root del progetto.

Linux, consigliato su Ubuntu/Debian/Lubuntu:

```bash
bash install-linux.sh
```

Windows 10 Home, da PowerShell amministratore:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install-windows.ps1
```

Poi apri:

```text
http://IP_DELLA_VM:7681
```

Comandi rapidi per il servizio web:

```bash
bash start-linux.sh
bash stop-linux.sh
```

```powershell
.\start-windows.ps1
.\stop-windows.ps1
```

Guide dettagliate:

- Panoramica: `deploy/README.md`
- Linux: `deploy/linux/README.md`
- Windows: `deploy/windows/README.md`

## Verifica

Verifica completa:

```powershell
python -m unittest discover -s tests -p "test*.py" -v
python -m compileall -q -x "node_modules|\.git|\.venv|winner_bot" .
```
