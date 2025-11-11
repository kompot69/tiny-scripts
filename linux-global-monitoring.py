#!/usr/bin/env python3
import subprocess
import time
import os
import re
import hashlib
# ================= CONFIG =================
CHECK_INTERVAL_SEC = 15
CHECK_DISK_INTERVAL_MIN = 30
NOTIFY_CMD = 'bash /srv/telegram_notify.sh "{message}"'
CHECK_SSH = True
CHECK_DISK_SPACE = True
CHECK_DISK_SMART = False
CHECK_LOAD = True
CHECK_SUDO = True
CHECK_TRAFFIC = True
CHECK_NETCFG = True
CHECK_PORTS = True
CHECK_SYSTEMD = True
CHECK_SYSTEMD_SERVICES = ["ssh", "ssh_port_forward", "ufw", "tor", "hikka", "comfyui", "transmission-daemon", "smbd", "mcpes", "mirror-bot", "ptpit-igor",]
OVERLOAD_WARN = 7.0 # Порог загрузки (например, 4 ядра → 4.0 == 100%)
MEM_WARN_PERCENT = 90
TRAFFIC_SPIKE_MBPS = 100
# ===========================================

last_netcfg_hash = ""
last_ports = set()
last_sudo_hash = ""
last_disk_check = 0
last_ssh_timestamp  = time.time()
last_service_states = {}
smart_notified_missing = False

def notify(msg): subprocess.call(f'{NOTIFY_CMD.format(message=msg)}', shell=True)

def check_ssh_attempts():
    """
    Отслеживает успешные и неудачные попытки SSH-входа.
    Работает и с /var/log/auth.log, и с journalctl (если нет auth.log).
    """
    global last_ssh_timestamp
    entries = []

    # --- 1. Попробуем использовать journalctl ---
    try:
        cmd = [
            "journalctl",
            "_COMM=sshd",
            "--since", f"@{int(last_ssh_timestamp)}",
            "--output", "short-unix",
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            try:
                ts_str, msg = line.split(" ", 1)
                ts = float(ts_str)
                if ts > last_ssh_timestamp: entries.append((ts, msg))
            except ValueError: continue
    except (FileNotFoundError, subprocess.CalledProcessError):
        # --- 2. Fallback: читаем /var/log/auth.log ---
        log = "/var/log/auth.log"
        if not os.path.exists(log): return
        try:
            stat = os.stat(log)
            ts = stat.st_mtime
            if ts <= last_ssh_timestamp: return
            with open(log, "r", errors="ignore") as f: lines = f.readlines()[-1000:]  # не читаем огромный лог
            for line in lines: entries.append((ts, line.strip()))
        except Exception: return
    # --- 3. Анализ записей ---
    for ts, line in entries:
        if last_ssh_timestamp == 0: continue
        if re.search(r"Failed password for", line): notify("SSH login failed: " + line.strip())
        elif re.search(r"Accepted (password|publickey)", line): notify("SSH login success: " + line.strip())
        elif re.search(r"pam_unix\(sshd:session\): session opened for user", line): notify("SSH session opened: " + line.strip())
        elif re.search(r"pam_unix\(sshd:session\): session closed for user", line): notify("SSH session closed: " + line.strip())
    # --- 4. Обновляем метку времени ---
    if entries: last_ssh_timestamp = max(ts for ts, _ in entries)
    else: last_ssh_timestamp = time.time()

# ---------- Systemd сервисы ----------
def check_systemd_services():
    global last_service_states
    for svc in CHECK_SYSTEMD_SERVICES:
        try: # Получаем основной статус
            status = subprocess.check_output(
                ["systemctl", "is-active", svc], text=True
            ).strip()

            # Если сервис не "active" — собираем подробности
            if status not in ("active", "activating"):
                # Проверяем, изменилось ли состояние по сравнению с предыдущим
                if last_service_states.get(svc) != status:
                    details = subprocess.check_output(
                        ["systemctl", "status", svc, "--no-pager", "--lines=5"], text=True
                    ).strip()
                    notify(f"Service '{svc}' abnormal state: {status}\n{details}")
            # Обновляем сохранённое состояние
            last_service_states[svc] = status

        except subprocess.CalledProcessError:
            if last_service_states.get(svc) != "error":
                notify(f"Failed to check service '{svc}' - systemctl returned error")
                last_service_states[svc] = "error"
        except Exception as e: notify(f"Error checking service '{svc}': {e}")

# ---------- Диск ----------
def check_disk_space():
    try:
        output = subprocess.check_output(["df", "-h", "/"], text=True).splitlines()
        if len(output) >= 2:
            usage_percent = int(re.findall(r"(\d+)%", output[1])[0])
            if usage_percent >= 90:
                notify(f"Low disk space: {usage_percent}% used")
    except Exception: pass

# ---------- SMART ----------
def check_smart_status():
    global smart_notified_missing
    try: subprocess.check_output(["which", "smartctl"])
    except subprocess.CalledProcessError:
        if not smart_notified_missing:
            notify("SMART check skipped: smartctl not found")
            smart_notified_missing = True
        return

    try:
        disks = [
            d
            for d in os.listdir("/dev")
            if re.match(r"sd[a-z]$", d) or re.match(r"nvme\d+n\d+$", d)
        ]
        for disk in disks:
            try:
                out = subprocess.check_output(
                    ["smartctl", "-H", f"/dev/{disk}"], text=True, stderr=subprocess.DEVNULL
                )
                if "PASSED" not in out:
                    notify(f"SMART warning on {disk}: {out.strip()}")
            except subprocess.CalledProcessError:
                pass
    except Exception:
        pass

# ---------- Нагрузка ----------
def check_load_memory():
    try:
        with open("/proc/loadavg") as f: load = float(f.read().split()[0])
        if load > OVERLOAD_WARN: notify(f"High load average: {load}")
        meminfo = open("/proc/meminfo").read()
        total = int(re.search(r"MemTotal:\s+(\d+)", meminfo).group(1))
        avail = int(re.search(r"MemAvailable:\s+(\d+)", meminfo).group(1))
        used_percent = (1 - avail / total) * 100
        if used_percent >= MEM_WARN_PERCENT: notify(f"High memory usage: {used_percent:.1f}%")
    except Exception: pass

# ---------- sudoers ----------
def check_sudoers():
    global last_sudo_hash
    try:
        data = ""
        for f in ["/etc/sudoers"] + [os.path.join("/etc/sudoers.d", x) for x in os.listdir("/etc/sudoers.d") if not x.startswith(".")]:
            if os.path.exists(f): data += open(f).read()
        h = hashlib.sha256(data.encode()).hexdigest()
        if last_sudo_hash and h != last_sudo_hash:
            notify("Sudoers configuration changed!")
        last_sudo_hash = h
    except Exception: pass

# ---------- Сеть ----------
def check_traffic():
    try:
        stats1 = {}
        with open("/proc/net/dev") as f:
            for line in f:
                if ":" in line:
                    iface, vals = line.split(":")
                    iface = iface.strip()
                    vals = vals.split()
                    stats1[iface] = (int(vals[0]), int(vals[8]))  # rx, tx
        time.sleep(1)
        stats2 = {}
        with open("/proc/net/dev") as f:
            for line in f:
                if ":" in line:
                    iface, vals = line.split(":")
                    iface = iface.strip()
                    vals = vals.split()
                    stats2[iface] = (int(vals[0]), int(vals[8]))

        for iface in stats1:
            rx_diff = (stats2[iface][0] - stats1[iface][0]) / 1024 / 1024 * 8
            tx_diff = (stats2[iface][1] - stats1[iface][1]) / 1024 / 1024 * 8
            if rx_diff > TRAFFIC_SPIKE_MBPS or tx_diff > TRAFFIC_SPIKE_MBPS:
                notify(f"Traffic spike on {iface}: {rx_diff:.1f}/{tx_diff:.1f} Mbps")
    except Exception: pass

# ---------- Изменение сети ----------
def check_netcfg():
    global last_netcfg_hash
    try:
        out = subprocess.check_output(["ip", "-br", "addr"], text=True) + subprocess.check_output(["ip", "route"], text=True)
        h = hashlib.sha256(out.encode()).hexdigest()
        if last_netcfg_hash and h != last_netcfg_hash: notify("Network configuration changed!")
        last_netcfg_hash = h
    except Exception:
        pass

# ---------- Порты ----------
def check_ports():
    global last_ports
    try: # Получаем список слушающих сокетов
        out = subprocess.check_output(["ss", "-tuln"], text=True)
        # Парсим: каждая строка с 'LISTEN' содержит протокол и адрес:порт
        current_ports = set()
        for line in out.splitlines():
            if "LISTEN" in line:
                parts = line.split()
                proto = parts[0]
                # Последняя колонка обычно содержит локальный адрес
                addr = parts[-2] if len(parts) >= 5 else ""
                current_ports.add(f"{proto} {addr}")
        if last_ports: # Если уже есть предыдущее состояние — сравниваем
            added = current_ports - last_ports
            removed = last_ports - current_ports
            if added or removed:
                msg = "Listening ports changed:\n"
                if added: msg += "\nNew ports:\n" + "\n ".join(sorted(added))
                if removed: msg += "\nClosed ports:\n" + "\n ".join(sorted(removed))
                notify(msg)
        last_ports = current_ports # Обновляем текущее состояние
    except subprocess.CalledProcessError: pass
    except FileNotFoundError: notify("Command 'ss' not found — skipping port check")
    except Exception as e: notify(f"Port check error: {e}")


# ================= MAIN LOOP =================
notify("Server monitoring started")
while True:
    if CHECK_SSH: check_ssh_attempts()
    if CHECK_SYSTEMD: check_systemd_services()
    if CHECK_LOAD: check_load_memory()
    if CHECK_SUDO: check_sudoers()
    if CHECK_TRAFFIC: check_traffic()
    if CHECK_NETCFG: check_netcfg()
    if CHECK_PORTS: check_ports()
    if CHECK_DISK_SMART or CHECK_DISK_SPACE:
        now = time.time()
        if now - last_disk_check >= CHECK_DISK_INTERVAL_MIN * 60:
            if CHECK_DISK_SPACE: check_disk_space()
            if CHECK_DISK_SMART: check_smart_status()
            last_disk_check = now
    time.sleep(CHECK_INTERVAL_SEC)
