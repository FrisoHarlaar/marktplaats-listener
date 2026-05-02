# Marktplaats Price Listener

Bewaakt meerdere Marktplaats-zoekopdrachten op nieuwe advertenties en stuurt
een **Telegram-melding** zodra er een nieuwe listing onder jouw prijslimiet verschijnt.

---

## Hoe het werkt

1. De listener haalt elke N minuten de nieuwste Marktplaats-advertenties op voor
   elke zoekopdracht in `config.yaml`.
2. Nieuwe advertenties (nog niet eerder gezien) worden opgeslagen in een lokale
   SQLite-database.
3. Als de prijs onder jouw limiet ligt, ontvang je een Telegram-bericht met
   titel, prijs, locatie en directe link.

---

## Installatie op Ubuntu

### 1. Repository clonen

```bash
git clone https://github.com/FrisoHarlaar/marktplaats-listener.git
cd marktplaats-listener
```

### 2. uv installeren (eenmalig)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env   # of herstart je terminal
```

### 3. Afhankelijkheden installeren

```bash
uv sync
```

`uv` maakt automatisch een `.venv` aan en installeert alle afhankelijkheden
uit `pyproject.toml` en `uv.lock`.

### 4. Telegram Bot aanmaken

1. Open Telegram en zoek op **@BotFather**.
2. Stuur `/newbot` en volg de instructies. Je krijgt een **bot token**.
3. Zoek op **@userinfobot** en stuur `/start` om je **chat ID** op te vragen.

### 5. Config aanmaken

```bash
cp config.example.yaml config.yaml
nano config.yaml
```

Vul in:
- `bot_token` — het token van @BotFather
- `chat_id` — jouw chat ID van @userinfobot
- `queries` — de zoekopdrachten die je wilt bewaken

### 6. Handmatig testen

```bash
uv run python listener.py
```

Je zou binnen enkele seconden een Telegram-bericht moeten ontvangen met
"Marktplaats Listener gestart". Als er meteen een advertentie overeenkomt,
krijg je ook die melding.

Druk op **Ctrl+C** om te stoppen.

---

## Als systemd-service draaien (aanbevolen)

### 1. Service-bestand aanpassen en kopiëren

```bash
# Pas YOUR_USERNAME aan naar jouw Ubuntu-gebruikersnaam
sed -i "s/YOUR_USERNAME/$(whoami)/g" marktplaats-listener.service
sudo cp marktplaats-listener.service /etc/systemd/system/
```

### 2. Service activeren

```bash
sudo systemctl daemon-reload
sudo systemctl enable marktplaats-listener
sudo systemctl start marktplaats-listener
```

### 3. Status controleren

```bash
sudo systemctl status marktplaats-listener

# Logs bekijken (live):
sudo journalctl -u marktplaats-listener -f
```

### 4. Service stoppen of herstarten

```bash
sudo systemctl stop marktplaats-listener
sudo systemctl restart marktplaats-listener
```

---

## Zoekopdrachten aanpassen

Bewerk `config.yaml` en herstart de service:

```bash
nano config.yaml
sudo systemctl restart marktplaats-listener
```

Voorbeeld — zonder prijslimiet:
```yaml
queries:
  - keyword: "Gazelle elektrische fiets"
  - keyword: "PlayStation 5"
    max_price: 450
```

---

## Bestandsstructuur

```
marktplaats-listener/
├── listener.py              # Hoofdloop
├── search.py                # Marktplaats-zoekopdrachten
├── notifier.py              # Telegram-meldingen
├── db.py                    # SQLite opslag (geziene advertenties)
├── config_loader.py         # Config-parser
├── config.yaml              # Jouw instellingen (niet committen!)
├── config.example.yaml      # Voorbeeld-config
├── pyproject.toml           # Project-metadata en afhankelijkheden (uv)
├── uv.lock                  # Lockfile met exacte versies
├── marktplaats-listener.service  # systemd unit-bestand
└── data/
    └── seen.db              # Automatisch aangemaakt
```

---

## Opmerkingen

- De `marktplaats` Python-package gebruikt de interne Marktplaats-API.
  Bij grote site-updates kan de package tijdelijk breken. Update dan via:
  `uv add marktplaats@latest`.
- Poll minimaal elke 5 minuten om rate limiting te vermijden.
- `data/seen.db` wordt automatisch aangemaakt. Advertenties ouder dan
  60 dagen worden automatisch verwijderd om de database klein te houden.
- `config.yaml` en `data/` staan in `.gitignore` — je token wordt nooit gecommit.
