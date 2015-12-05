#!/system/bin/sh

# SuperSu only runs the first script in su.d. This one calls the others.

/system/su.d/91firewall
/system/su.d/Y02firstboot
