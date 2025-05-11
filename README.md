# Nástroj CyberTool 🛡️

## ✨ Popis projektu

CyberTool je webová aplikace určená pro simulaci útoků včetně rozpoznání zranitelných služeb, jejich zneužití a vyhodnocení reakcí obranných mechanismů. Umožňuje definovat vlastní ústupové scénáře, jež se provádí krok po kroku, a poskytuje uživateli průěžné informace pomocí WebSocketů.

Aplikace je postavena na frameworku **Django** a používá **ASGI server Daphne** pro podporu asynchronních požadavků a WebSocket komunikace.

---

## 🚧 Závislosti

K úspěšnému spuštění aplikace jsou potřeba následující nástroje:

### Systémové balíčky:

* `docker`
* `docker-compose`
* `python3.8+`
* `python3-venv`
* `nmap`
* `tshark`
* `hping3`

> Většina testovacích funkcí vyžaduje administrátorská oprávnění (např. pro spouštění paketových útoků nebo manipulaci se síťovými rozhraními).

---

## 🔧 Instalace

1. **Klonování repozitáře**

```bash
git clone https://github.com/tvoje-uzivatelske-jmeno/cybertool.git
cd cybertool
```

2. **Vytvoření a aktivace virtuálního prostředí**

```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Instalace python balíčků**

```bash
pip install -r requirements.txt
```

4. **Build & start Docker kontejnerů** (na pozadí)

```bash
sudo docker-compose up -d
```

5. **Migrace databáze**

```bash
python manage.py migrate
```

6. **Spuštění ASGI serveru Daphne**

```bash
sudo daphne -b 127.0.0.1 -p 8000 cybertool.asgi:application
```

---

## 🚀 Spuštění aplikace

Po plném spuštění jsou dostupné adresy:

```
http://127.0.0.1:8000 - hlavní rozhraní nástroje
```

---

## ⚠️ Poznámka ke spouštění pod rootem

Aplikace používá nástroje, jako je `tshark` nebo `hping3`, které vyžadují root oprávnění. Nejjednodušší cestou je tedy spouštění přes `sudo`. Pokud je to možné, doporučuje se vytvořit sandboxové prostředí nebo použít rozšířená oprávnění pouze pro konkrétní nástroje (např. pomocí `capabilities`).

---

## 📁 Struktura projektu

* `core/` – hlavní logika aplikace (scénáře, websockety, akce)
* `templates/` – HTML šablony
* `scripts/` – Python skripty pro vzdálené spouštění přes SSH
* `files/` – lokálně připravené knihovny nebo doplňkové soubory

---

## 🎓 Licence a autor

Tento projekt je součástí diplomové práce a slouží k výzkumným a vzdělávacím účelům.
