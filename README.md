# Nástroj CyberTool 🛡️

## ✨ Popis projektu

CyberTool je webová aplikace určená pro vytváření automatizovaných útoků se začleněním obranné reakce modrých týmů. Nástroj má sloužit pro výukové účely, kdy se modrý tým bude učit zdokonalit své reakce na probíhající útok, přičemž nástroj má za úkol hledat alternativní cesty průchodu ke svému cíli a zmařit snahu obranného týmu.

Nástroj obsahuje scénáře, jež jsou uloženy v databázi MongoDB, pro jednoduchou správu databáze je implementováno rozhraní Mongo Express.

Aplikace je postavena na frameworku **Django** a používá **ASGI server Daphne** pro podporu asynchronních požadavků a WebSocket komunikace.
Po spuštění scénáře jsou uživateli poskytnuty průběžné informace o průběhu útoku.

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

6. **Spuštění samotného nástroje**

```bash
sudo venv/bin/daphne -b 127.0.0.1 -p 8000 cybertool.asgi:application
```
> Většina využívaných funkcí vyžaduje administrátorská oprávnění, proto je třeba spouštet nástroj za použití sudo. 
---

## 🚀 Spuštění aplikace

Po plném spuštění jsou dostupné adresy:

1. **Hlavní rozhraní nástroje**
```
http://127.0.0.1:8000
```
1. **Rozhraní Mongo Express pro správu scénářů a akcí**
```
http://127.0.0.1:8081
```
1. **Rozhraní síťové monitoringu Arkime**
```
http://127.0.0.1:8005
```
> Přihlašovací udaje:
> **uživatel**: arkime
> **heslo**: arkime
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
## 🛠️ Nezbytná infrastruktura pro běh aktuálních scénářů
Databáze obsahuje tři scénáře, pro úspěšné použití těchto scénářů je potřeba mít stejné testovací prostředi, pro které jsou nastaveny, nebo upravit potřebné části jednotlivých scénářů.
Níže jsou rozepsány potřebné časti infrastruktury pro každý ze scénářů.

1. **Scénář 1: Nalezení VMWare zařízení a pingflood na něj s alternativní taktikou na blokaci**
   * => 1 VMWare zařízení v síti (Virtálka) > nutně být nemusí, pokud scénář takový systém nenajde, zaútočí na defatulní IP (viz níže)
   * systém s IP adresou 192.168.50.12 > Použito jako defaultní IP adresa útoku v případě, že není nalezeno VMware zařízení
   * systém s dostupnou utilitou hping3 a ssh pod IP 192.168.50.18, s uživatelským jménem "utko" a heslem "radegast12" > při testování použito Raspberry Pi
3. **Scénář 2: Identifikace zranitelností metasploitu, zneužití a spuštění UDP floodu ze získaného zařízení.**
4. **Scénář 3: Nalezení PLC zařízení, injekce kodu pro zastavení běhu programu. Reakce na opravu kódu či blokaci útočníka.**

---
## 📌 

---



## 🎓 Licence a autor

Tento projekt je součástí diplomové práce a slouží k výzkumným a vzdělávacím účelům.
