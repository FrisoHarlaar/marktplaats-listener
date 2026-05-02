# Marktplaats Price Listener

Bewaakt meerdere Marktplaats-zoekopdrachten op nieuwe advertenties en stuurt
een **Telegram-melding** zodra er een nieuwe listing onder jouw prijslimiet verschijnt.

Zoekopdrachten beheer je volledig via Telegram — geen configuratiebestand nodig.

---

## Telegram commando's

| Commando | Omschrijving |
|---|---|
| `/add <zoekterm> [max:<prijs>]` | Voeg een zoekopdracht toe |
| `/remove <zoekterm>` | Verwijder een zoekopdracht |
| `/list` | Bekijk alle actieve zoekopdrachten |
| `/help` | Toon beschikbare commando's |

**Voorbeelden:**
```
/add iPhone 14 Pro max:700
/add MacBook Air M2
/add Sony WH-1000XM5 max:200
/remove MacBook Air M2
/list
```

---

## Hoe het werkt

1. De bot draait als achtergrondproces op je Ubuntu server.
2. Elke N minuten worden alle actieve zoekopdrachten gecontroleerd op Marktplaats.
3. Nieuwe advertenties (nog niet eerder gezien) worden opgeslagen in een lokale SQLite-database.
4. Als de prijs onder jouw limiet ligt, ontvang je een Telegram-bericht met titel, prijs, locatie en directe link.
5. Zoekopdrachten toevoegen of verwijderen doe je live via Telegram — geen herstart nodig.

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

### 4. Telegram Bot aanmaken

1. Open Telegram en zoek op **@BotFather**.
2. Stuur `/newbot` en volg de instructies. Je krijgt een **bot token**.
3. Zoek op **@userinfobot** en stuur `/start` om je **chat ID** op te vragen.

### 5. Config aanmaken

```bash
cp config.example.yaml config.yaml
nano config.yaml
```

Vul alleen in:
- `bot_token` — het token van @BotFather
- `chat_id` — jouw chat ID van @userinfobot

Zoekopdrachten voeg je later toe via Telegram.

### 6. Handmatig testen

```bash
uv run python listener.py
```

Je ontvangt een Telegram-bericht "Marktplaats Listener gestart". Voeg daarna een
zoekopdracht toe via `/add` en wacht op de eerste poll (standaard 5 minuten).

Druk op **Ctrl+C** om te stoppen.

---

## Als systemd-service draaien (aanbevolen)

### 1. Pad naar uv achterhalen

```bash
which uv   # bijv. /home/friso/.local/bin/uv
```

### 2. Service-bestand aanpassen en kopiëren

Open `marktplaats-listener.service` en pas `User` en `WorkingDirectory` aan.
Controleer ook of het pad naar `uv` klopt (`ExecStart=uv run python listener.py`
werkt als `uv` in `$PATH` staat; anders volledig pad opgeven).

```bash
sed -i "s/YOUR_USERNAME/$(whoami)/g" marktplaats-listener.service
sudo cp marktplaats-listener.service /etc/systemd/system/
```

### 3. Service activeren

```bash
sudo systemctl daemon-reload
sudo systemctl enable marktplaats-listener
sudo systemctl start marktplaats-listener
```

### 4. Status en logs

```bash
sudo systemctl status marktplaats-listener

# Live logs:
sudo journalctl -u marktplaats-listener -f
```

### 5. Herstarten na config-wijziging

```bash
sudo systemctl restart marktplaats-listener
```

---

## Bestandsstructuur

```
marktplaats-listener/
├── listener.py              # Telegram bot + achtergrond-pollloop
├── search.py                # Marktplaats-zoekopdrachten
├── notifier.py              # Berichtopmaak
├── db.py                    # SQLite: geziene advertenties + actieve queries
├── config_loader.py         # Config-parser
├── config.yaml              # Jouw instellingen (niet committen!)
├── config.example.yaml      # Voorbeeld-config
├── pyproject.toml           # Project-metadata en afhankelijkheden (uv)
├── uv.lock                  # Lockfile met exacte versies
├── marktplaats-listener.service  # systemd unit-bestand
└── data/
    └── seen.db              # Automatisch aangemaakt (queries + geziene ads)
```

---

## Opmerkingen

- De `marktplaats` Python-package gebruikt de interne Marktplaats-API.
  Bij grote site-updates kan de package tijdelijk breken. Update dan via:
  `uv add marktplaats@latest` en herstart de service.
- Poll minimaal elke 5 minuten om rate limiting te vermijden.
- Alleen berichten van jouw `chat_id` worden geaccepteerd — de bot reageert
  niet op commando's van anderen.
- `config.yaml` en `data/` staan in `.gitignore` — je token wordt nooit gecommit.
