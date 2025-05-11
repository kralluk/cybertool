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
> Prvotní start Dockeru může trvat poměrně dlouho dobu, vzhledem ke stahování a vytvářeních všech potřebných Docker obrazů a závislotí.
> Samotný proces inicializace všech kontejnerů taky zabere zhruba minutu až dvě, vzhledem k poměrně náročnému procesu spuštění Arkime.
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
## 🛠️ Nezbytná infrastruktura pro běh aktuálních scénářů
Databáze obsahuje tři scénáře, pro úspěšné použití těchto scénářů je potřeba mít stejné testovací prostředi, pro které jsou nastaveny, nebo upravit potřebné části jednotlivých scénářů.
Níže jsou rozepsány potřebné časti infrastruktury pro každý ze scénářů.

1. **Scénář 1: Nalezení VMWare zařízení a pingflood na něj s alternativní taktikou na blokaci**
   * => 1 VMWare zařízení v síti (Virtuálka)
     > Nutně být nemusí, pokud scénář takový systém nenajde, zaútočí na defatulní IP (viz níže).
   * Systém s IP adresou 192.168.50.12
     > Použito jako defaultní IP adresa útoku v případě, že není nalezeno VMware zařízení.
   * Systém s dostupnou utilitou hping3 a ssh pod IP 192.168.50.18, s uživatelským jménem "utko" a heslem "radegast12"
     > Při testování použito Raspberry Pi, IP adresu i přihlašovací údaje lze připadně změnit v parametrech scénáře.
3. **Scénář 2: Identifikace zranitelností metasploitu, zneužití a spuštění UDP floodu ze získaného zařízení.**
   * Systém, na kterém se nachází zranitelnost UnrealIRCD 3.2.8.1 Backdoor nebo VSFTPD v2.3.4 Backdoor
     > Nejjednoduší je použít VM Metasploitable 2 (https://www.rapid7.com/products/metasploit/metasploitable/).
   * Systém s IP adresou 192.168.50.12
     > Na tuto IP je proveden UDP flood, také je možno si ji přepsat ve scénáři dle potřeby.
5. **Scénář 3: Nalezení PLC zařízení, injekce kodu pro zastavení běhu programu. Reakce na opravu kódu či blokaci útočníka.**
   * PLC s otevřeným portem 102 protokolu S7
   * Systém s IP adresou 192.168.50.12 a povoleným ssh s uživatelským jménem "test" a heslem "test"
   * ❗Nutnost změnit ve scénáří použitou knihovnu v kroku číslo 6 (step_id: 6) použitou knihovnu pro nahrání dle procesorové architektury cílového zařízení
     > Defaultní je knihovna pro ARM64, ve složce *files* se, pro případ potřeby, nachází i pro achitekturu x86_64, stačí tedy pouze hodnotu parametru *file_name* na odpovídající soubor.
     
---
## 📌 Důležité adresáře a konfigurační soubory
* `scripts/` – Python skripty pro vzdálené spouštění přes SSH
  > Tyto skripty bere akce *ssh_run_python_script*.
* `files/` – soubory, které bere akce
  > Tyto soubory bere akce *ssh_upload_file*.
* `arkime/etc/config.ini` – Konfigurační soubor pro Arkime 
  > Podstatná je část **interface**, zde lze středníkem oddělit monirované interfacy (defautlně se monitoruje eth0 a eth1). Po změně je nutné restartovat Docker Compose a tím opakovat inicializnační proces.
---

## 🎓 Licence a autor

Tento projekt je součástí diplomové práce a slouží k výzkumným a vzdělávacím účelům.
