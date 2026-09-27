
Throughout this assessment, on a CentOS 10 VM: package management (dnf), systemd service management (postgresql, kubelet), user/permission management (deployer/root, least-privilege DB roles), process/port inspection (ps, ss), log inspection (journalctl, kubectl logs), firewall/network config (pg_hba.conf, listen_addresses), and real incident diagnosis under load (see investigation/INCIDENT-001-RCA.md, investigation/docker-postgres-connectivity.md for full command trails).

Representative commands used: `sudo dnf install`, `sudo systemctl status/restart/reload`, `sudo -u postgres psql`, `ss -tlnp`, `ps aux`, `kubectl describe/logs`, `journalctl -u postgresql`.
