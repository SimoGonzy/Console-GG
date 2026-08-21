# Deploy

Console GG puo essere giocato dal browser su una VM o un piccolo PC nella rete
locale.

## Scelta Rapida

- Linux/Lubuntu consigliato: `bash install-linux.sh`
- Windows 10 Home: `.\install-windows.ps1`

Entrambi espongono il cabinato su:

```text
http://IP_DELLA_MACCHINA:7681
```

## Avvio E Stop

Linux Docker:

```bash
bash start-linux.sh
bash stop-linux.sh
```

Windows:

```powershell
.\start-windows.ps1
.\stop-windows.ps1
```

## Guide Dettagliate

- Linux: `deploy/linux/README.md`
- Windows: `deploy/windows/README.md`

Tieni il servizio esposto solo su una rete locale fidata. Per accesso da fuori,
usa VPN, firewall o reverse proxy con autenticazione e TLS.
