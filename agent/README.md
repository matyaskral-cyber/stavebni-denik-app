# Stavební deník — On-premise Sync Agent

Zálohovací agent pro lokální ukládání dat ze Stavebního deníku.

## Instalace

```bash
cp config.example.json config.json
# Vyplňte api_url, api_key a local_path
```

## Použití

```bash
node sync-agent.js
```

## Automatický cron

```cron
# Každý den ve 4:00
0 4 * * * cd /opt/agent && node sync-agent.js >> /var/log/backup.log 2>&1
```

## Konfigurace

| Klíč | Popis |
|------|-------|
| `api_url` | URL export endpointu (např. `https://app.example.com/kamenicka/api/backup/export`) |
| `api_key` | API klíč vygenerovaný v nastavení firmy |
| `local_path` | Cesta pro ukládání záloh |
| `firma_slug` | Slug firmy (pro pojmenování souborů) |

## Delta sync

Při prvním spuštění se stáhne kompletní záloha. Při dalších spuštěních se stáhnou pouze záznamy deníku od posledního syncu (soubor `last_sync.json`).

Pro vynucení full syncu smažte `last_sync.json`.
