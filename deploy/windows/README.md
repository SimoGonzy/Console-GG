# Deploy Windows 10 Home

Modalita consigliata: **Console GG Arcade**. La VM resta accesa come cabinato:

- apri `http://IP_DELLA_VM:7681` e giochi subito dal browser;
- oppure fai `ssh arcade@IP_DELLA_VM` e il menu parte subito, senza comandi extra;
- il servizio browser viene avviato automaticamente all'accensione della VM.

Su Windows Home il servizio browser viene gestito come servizio Windows tramite Scheduled Task
(`ConsoleGG Arcade Web`), eseguito come `SYSTEM` con restart e avvio al boot.

## Requisiti

- Windows 10 Home aggiornato.
- PowerShell aperto come amministratore.
- Python 3.11+ installato e nel `PATH`.
- Node.js LTS installato e nel `PATH`, preferibilmente con installer standard
  per tutti gli utenti. Il task automatico parte come `SYSTEM`.
- Una password per l'utente SSH `arcade` quando lo script la chiede.

## Installazione Arcade

Dalla root del progetto, dentro la VM:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install-windows.ps1
```

Con whitelist/login browser:

```powershell
.\install-windows.ps1 `
  -AllowedUsers "simone,arcade" `
  -AccessCode "cambia-questo-codice"
```

Questa configurazione passa al servizio browser le variabili
`CONSOLE_GG_ALLOWED_USERS` e `CONSOLE_GG_ACCESS_CODE`. Se vuoi separare il
segreto usato per firmare i cookie, aggiungi anche `-SessionSecret`.

Lo script:

- installa/copia Console GG in `C:\ConsoleGG`;
- crea `.venv` e installa il comando `console-gg`;
- installa le dipendenze Node del web terminal;
- registra il task Windows `ConsoleGG Arcade Web`;
- lo avvia subito e lo configura per ripartire automaticamente al boot;
- abilita whitelist/login browser quando passi `-AllowedUsers` o `-AccessCode`;
- apre la porta TCP `7681`;
- configura OpenSSH sulla porta `22`;
- crea, se manca, l'utente locale `arcade`;
- aggiunge un `ForceCommand` SSH per far partire subito il gioco.

Trova l'IP della VM:

```powershell
ipconfig
```

Apri dal browser:

```text
http://IP_DELLA_VM:7681
```

NON usare `https://` su questa porta: il cabinato browser parla HTTP semplice.
Se il browser mostra `SSL ha ricevuto un pacchetto che eccede la dimensione
massima consentita`, sta provando HTTPS contro un servizio HTTP.

Oppure entra via SSH:

```powershell
ssh arcade@IP_DELLA_VM
```

Quando esci dal gioco, la sessione SSH si chiude. Nel browser puoi premere
`Reconnect` per aprire una nuova sessione.

## Comandi Utili Arcade

```powershell
Get-ScheduledTask "ConsoleGG Arcade Web"
.\start-windows.ps1
.\stop-windows.ps1
powershell -ExecutionPolicy Bypass -File C:\ConsoleGG\deploy\windows\start-arcade-web.ps1
```

Il servizio browser si avvia automaticamente al boot tramite il task Windows
`ConsoleGG Arcade Web`. Per abilitarlo o ripararlo senza rifare tutta
l'installazione:

```powershell
powershell -ExecutionPolicy Bypass -File C:\ConsoleGG\deploy\windows\enable-arcade-autostart.ps1
```

Con whitelist:

```powershell
powershell -ExecutionPolicy Bypass -File C:\ConsoleGG\deploy\windows\enable-arcade-autostart.ps1 `
  -AllowedUsers "simone,arcade" `
  -AccessCode "cambia-questo-codice"
```

Per rilanciare l'installazione senza riconfigurare SSH:

```powershell
.\install-windows.ps1 -SkipOpenSSH -SkipArcadeUser
```

## Diagnostica Connessione

Se SSH o browser non rispondono, esegui dentro la VM:

```powershell
powershell -ExecutionPolicy Bypass -File C:\ConsoleGG\deploy\windows\diagnose-network.ps1
```

Leggi soprattutto:

- `Test locale SSH 127.0.0.1:22`: se e `False`, il problema e OpenSSH dentro la VM;
- `Test locale Web 127.0.0.1:7681`: per Arcade controlla il task `ConsoleGG Arcade Web`;
- se i servizi locali sono OK ma da fuori non entra, il problema e quasi sempre rete VM/NAT.

Nel caso NAT, usa una di queste strade:

- metti la scheda della VM in modalita `Bridged/Scheda con bridge`;
- oppure configura port forwarding:
  host `2222` -> guest `22`, host `7681` -> guest `7681`.

Con port forwarding:

```powershell
ssh -p 2222 arcade@127.0.0.1
```

```text
http://127.0.0.1:7681
```

## Installazione SSH Base

Se vuoi solo copiare il progetto e configurare SSH manualmente:

```powershell
.\deploy\windows\install-windows-ssh.ps1
```

Se vuoi installare solo Console GG e configurare SSH a parte:

```powershell
.\deploy\windows\install-windows-ssh.ps1 -SkipOpenSSH
```

### Se `sshd` Non Viene Trovato

Su alcune installazioni di Windows 10 Home la capability `OpenSSH.Server` non e
disponibile o non crea il servizio `sshd`. In quel caso lo script si ferma con
una diagnosi invece di fallire su `Set-Service`.

Controlla cosa vede Windows:

```powershell
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
```

Poi scegli una di queste strade:

- installa `OpenSSH Server` da `Impostazioni > App > Funzionalita facoltative`;
- installa OpenSSH con un MSI e rilancia:

```powershell
.\deploy\windows\install-windows-ssh.ps1 -OpenSshMsiPath C:\Downloads\OpenSSH-Win64.msi
```

- oppure rilancia con `-SkipOpenSSH`.

## Browser Legacy Con Wetty

Wetty resta disponibile come fallback, ma non e piu il percorso consigliato per
il cabinato perche richiede login SSH nel browser.

```powershell
powershell -ExecutionPolicy Bypass -File C:\ConsoleGG\deploy\windows\start-wetty.ps1
```

Poi apri:

```text
http://IP_DELLA_VM:7681
```

## Sicurezza

- Se non imposti `CONSOLE_GG_ALLOWED_USERS` o `CONSOLE_GG_ACCESS_CODE`, il browser
  resta senza login per uso rapido in LAN.
- Con whitelist attiva, il browser accetta solo username in
  `CONSOLE_GG_ALLOWED_USERS`; con `CONSOLE_GG_ACCESS_CODE` richiede anche il
  codice condiviso.
- L'utente SSH `arcade` richiede password o chiave: Windows non permette in modo
  sano login remoti con password vuota.
- Se la VM e raggiungibile da reti non fidate, usa VPN o firewall.
