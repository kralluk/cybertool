#!/bin/bash
echo "Spouštím přidání uživatele 'admin'..."
# Přidání uživatele, pokud již existuje, příkaz selže, ale ignorujeme chybu (|| true)
 /opt/arkime/bin/arkime_add_user.sh arkime "Admin User" arkime --admin || true
echo "Spouštím Arkime viewer..."
exec /opt/arkime/bin/docker.sh viewer
