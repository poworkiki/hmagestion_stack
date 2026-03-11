#!/bin/bash
# === HARDENING VPS HMA ===
echo "=== Début du hardening VPS HMA ==="

# 1. Fail2ban
echo ">>> Fail2ban..."
printf "[sshd]\nenabled = true\nport = ssh\nfilter = sshd\nlogpath = /var/log/auth.log\nmaxretry = 3\nbantime = 3600\nfindtime = 600\n" > /etc/fail2ban/jail.local
systemctl restart fail2ban
echo "Fail2ban OK"

# 2. SSH hardening
echo ">>> SSH hardening..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
sed -i 's/#PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sed -i 's/#LoginGraceTime.*/LoginGraceTime 30/' /etc/ssh/sshd_config
sed -i 's/X11Forwarding yes/X11Forwarding no/' /etc/ssh/sshd_config
echo "SSH OK"

# 3. Sysctl
echo ">>> Sysctl hardening..."
printf "net.ipv4.conf.all.rp_filter = 1\nnet.ipv4.conf.default.rp_filter = 1\nnet.ipv4.icmp_echo_ignore_broadcasts = 1\nnet.ipv4.conf.all.accept_redirects = 0\nnet.ipv4.conf.all.send_redirects = 0\nnet.ipv4.conf.all.accept_source_route = 0\nnet.ipv6.conf.all.accept_redirects = 0\n" > /etc/sysctl.d/99-hardening.conf
sysctl --system > /dev/null 2>&1
echo "Sysctl OK"

# 4. UFW check
echo ">>> UFW status..."
ufw status

echo ""
echo "=== HARDENING TERMINÉ ==="
echo "Redémarrage recommandé : reboot"
