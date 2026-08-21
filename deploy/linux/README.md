# Deploy Linux

Console GG puo essere esposto sulla rete locale in due modi:

- Docker Compose, consigliato per VM Linux dedicate.
- systemd + `ttyd`, fallback nativo senza Docker.

Entrambi i percorsi possono partire automaticamente al boot. I vecchi script
shell direttamente sotto `deploy/` restano wrapper verso questa cartella.

## Docker Compose Consigliato

Sulla VM Ubuntu/Debian/Lubuntu, dalla root del progetto:

```bash
bash install-linux.sh
```

Apri:

```text
http://IP_DELLA_VM:7681
```

Il container usa `restart: unless-stopped`, quindi riparte quando Docker riparte
al boot.

Comandi utili:

```bash
docker compose ps
docker logs -f console-gg
bash start-linux.sh
bash stop-linux.sh
bash deploy/diagnose-docker.sh
```

Se Docker richiede privilegi:

```bash
sudo bash start-linux.sh
```

Se vedi `permission denied` su `/var/run/docker.sock`, puoi aggiungere il tuo
utente al gruppo Docker e poi fare logout/login:

```bash
sudo usermod -aG docker "$USER"
```

### Login Docker Opzionale

`ttyd` puo proteggere il terminale con Basic Auth:

```bash
export CONSOLE_GG_TTYD_CREDENTIAL="arcade:cambia-questa-password"
bash start-linux.sh
```

Lascia la variabile vuota per mantenere l'accesso rapido in una LAN fidata.

## Linux Nativo systemd

Percorso alternativo senza Docker:

```bash
bash install-linux.sh native
```

Lo script:

- installa `python3`, `venv`, `pip`, `rsync` e `ttyd`;
- copia il progetto in `/opt/console-gg`;
- crea il comando `console-gg`;
- salva le statistiche in `/var/lib/console-gg/console_gg_stats.json`;
- installa `console-gg-ttyd.service`;
- lo abilita con `systemctl enable`, quindi parte automaticamente al boot.

Comandi utili:

```bash
sudo systemctl status console-gg-ttyd
sudo systemctl restart console-gg-ttyd
sudo journalctl -u console-gg-ttyd -f
```

Per riparare solo l'autostart senza reinstallare tutto:

```bash
bash deploy/enable-linux-autostart.sh
```

Per capire perche una VM headless non risponde dopo il boot:

```bash
bash deploy/diagnose-linux.sh
```

## Login Native ttyd Opzionale

L'installer crea `/etc/console-gg/console-gg.env`. Per abilitare Basic Auth:

```bash
sudo nano /etc/console-gg/console-gg.env
```

Imposta:

```bash
CONSOLE_GG_TTYD_CREDENTIAL=arcade:cambia-questa-password
```

Poi riavvia:

```bash
sudo systemctl restart console-gg-ttyd
```

## Porta E Firewall

Su Ubuntu con `ufw`:

```bash
sudo ufw allow 7681/tcp
sudo ufw status
```

Trova l'IP locale della VM:

```bash
hostname -I
```

Apri:

```text
http://IP_DELLA_VM:7681
```

## Sicurezza

Tienilo esposto solo sulla rete locale. Se la VM e raggiungibile da reti non
fidate, metti davanti una VPN o un reverse proxy con autenticazione e TLS.
