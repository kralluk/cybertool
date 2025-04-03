#!/bin/bash
echo "Spouštím přidání uživatele 'admin'..."
# Zkusíme přidat uživatele, pokud již existuje, příkaz selže, ale ignorujeme chybu (|| true)
 /opt/arkime/bin/arkime_add_user.sh arkime "Admin User" arkime --admin || true
echo "Spouštím Arkime viewer..."
exec /opt/arkime/bin/docker.sh viewer
