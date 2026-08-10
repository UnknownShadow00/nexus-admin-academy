"""Phase E (Weeks 18-20) curriculum content — Linux and Operations.

No new role gate here (Phase E sits between Gate 4 and the capstone's Gate 5);
Linux competence is assessed via TICKETS as the primary mechanism (master
prompt Part 3), and rolls into the Gate 5 mixed-incident requirements.

Infrastructure honesty: Linux labs run on a single Ubuntu 22.04 VM the mentor
clones by hand (MANUAL-VM), or a per-student clone; SSH access over Headscale.
Students can also use WSL or a local VM for command practice. NO requirement
depends on automated provisioning.
"""

from seed_phase_a import ANCHORS, NOTES_TEMPLATE, _q

MODULES_E = [
    {
        "code": "MOD-018",
        "title": "Linux Survival to Competence",
        "description": "Filesystem, navigation, files/permissions, users/groups, sudo, packages, SSH. Week 18.",
        "target_role": "Junior Systems Technician",
        "difficulty_band": 4,
        "estimated_hours": 16,
        "module_order": 19,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "The Linux Filesystem and Navigation",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Linux organizes everything under a single root (/), not per-drive letters. The "
                    "directories a technician meets constantly:\n"
                    "- / — the root of everything.\n"
                    "- /etc — configuration files (services, network, users). You'll edit and read these "
                    "endlessly.\n"
                    "- /var — variable data, crucially /var/log (logs!) and web content on some systems.\n"
                    "- /home — user home directories.\n"
                    "- /usr — installed programs and libraries.\n"
                    "- /tmp — temporary files.\n\n"
                    "NAVIGATION & INSPECTION (your daily verbs): pwd (where am I), ls -l (list with "
                    "details/permissions), cd (move), cat/less/tail (read files — tail -f follows a log "
                    "live), find and grep (locate files and search inside them). man <command> is the "
                    "built-in manual — the Linux equivalent of Get-Help; you are never stuck.\n\n"
                    "PATHS: absolute (/etc/ssh/sshd_config) vs relative (../logs). Tab-completion and up-"
                    "arrow history make you fast and prevent typos on dangerous commands.\n\n"
                    "THE MENTAL MODEL: 'everything is a file' — devices, config, even many system states "
                    "appear as files you can read. This is WHY log-reading and config inspection are the "
                    "core Linux troubleshooting skills, exactly like Event Viewer + services on Windows.\n\n"
                    "SAFETY: the command line has no undo and no recycle bin. rm deletes immediately; "
                    "rm -rf on the wrong path is catastrophic. Read your command before pressing Enter, "
                    "especially anything with rm, and never run destructive commands you don't understand.\n\n"
                    "COMMON MISTAKES: getting lost (forgetting pwd/ls); assuming a recycle bin exists; "
                    "running rm -rf carelessly; editing /etc files without a backup copy."
                ),
                "outcomes": [
                    "Navigate the Linux filesystem and identify the purpose of /etc, /var/log, /home, /usr",
                    "Inspect files and follow logs with ls, cat/less, tail -f, find, grep, and man",
                    "Apply command-line safety: no undo, read-before-Enter, back up config before editing",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Permissions, Users, Groups, and sudo",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "Linux permissions are simpler than NTFS once you see the pattern. Every file has an "
                    "OWNER, a GROUP, and OTHERS, each with read (r=4), write (w=2), execute (x=1). "
                    "ls -l shows them: -rwxr-x--- means owner rwx(7), group r-x(5), others ---(0), i.e. "
                    "750. chmod changes permissions (chmod 640 file, or chmod g+w file); chown changes "
                    "ownership (chown user:group file).\n\n"
                    "WHY x MATTERS: on a FILE, x = executable (a script/program). On a DIRECTORY, x = you "
                    "can enter it. A directory that's readable but not executable lists confusingly — a "
                    "classic 'permission denied' puzzle.\n\n"
                    "USERS & GROUPS: /etc/passwd (users) and /etc/group (groups); useradd/usermod, "
                    "groupadd; add a user to a group with usermod -aG group user (the -a is vital — "
                    "without it you REPLACE their groups). id <user> shows a user's groups.\n\n"
                    "sudo — the root rail: you don't log in as root; you run specific commands with sudo "
                    "(logged, auditable, least-privilege). 'Permission denied' on a system file usually "
                    "means 'you needed sudo' — but pause: is sudo actually appropriate here, or are you "
                    "about to change something you shouldn't? sudo is power; treat it like the admin "
                    "account it is.\n\n"
                    "THE ACCESS-DENIED INVESTIGATION (Linux): ls -l the file/dir → who owns it, what are "
                    "the perms → is the user the owner, in the group, or 'other'? → id the user to check "
                    "group membership → fix at the GROUP or ownership level, minimally. Same discipline as "
                    "Windows, different syntax.\n\n"
                    "COMMON MISTAKES: usermod -G without -a (wiping group memberships); chmod 777 to 'make "
                    "it work' (the Linux Full-Control sin); running everything as root instead of scoped "
                    "sudo; forgetting directory x."
                ),
                "outcomes": [
                    "Read and set Linux permissions (rwx / numeric) and ownership with chmod/chown",
                    "Manage users and group membership safely (usermod -aG) and inspect with id",
                    "Run the Linux access-denied investigation and apply least-privilege sudo",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Packages and SSH",
                "lesson_order": 3,
                "estimated_minutes": 75,
                "summary": (
                    "PACKAGE MANAGEMENT (Ubuntu/Debian apt): software comes from repositories, not random "
                    "downloads. apt update (refresh the package list), apt upgrade (install available "
                    "updates), apt install <pkg>, apt remove <pkg>. dpkg -l lists installed packages. This "
                    "is the patching skill from Windows, done cleanly: 'is this package installed and "
                    "current?' and 'apply security updates' are routine tasks. (Red Hat systems use dnf/"
                    "yum — awareness.)\n\n"
                    "SSH — how you reach Linux servers: ssh user@host opens a remote shell (the Linux "
                    "equivalent of RDP, but text). This is your primary access method for every Linux "
                    "ticket in this program. Key facts:\n"
                    "- KEYS beat passwords: an SSH key pair (private key stays with you, public key on the "
                    "server in ~/.ssh/authorized_keys) is more secure and is standard. You'll recognize "
                    "'Permission denied (publickey)' as a key/authorized_keys problem.\n"
                    "- The service is sshd, configured in /etc/ssh/sshd_config (port, whether root login "
                    "is allowed, password vs key auth). A config change needs a service restart to apply.\n"
                    "- Basic hardening awareness: disable root login, prefer keys, don't expose SSH "
                    "needlessly — the secure-administration theme from the switch lessons, on Linux.\n\n"
                    "TROUBLESHOOTING SSH ACCESS: can you reach the host at all (ping/port)? Is sshd "
                    "running? Right user/key? Right permissions on ~/.ssh (SSH refuses keys if the "
                    "permissions are too open — a famously confusing failure). The four-gate mindset from "
                    "RDP (Week 7) transfers directly.\n\n"
                    "COMMON MISTAKES: installing software outside the package manager; forgetting apt "
                    "update before install; wrong ~/.ssh permissions; editing sshd_config without "
                    "restarting sshd; locking yourself out by disabling password auth before keys work."
                ),
                "outcomes": [
                    "Manage packages and updates with apt (install, remove, update/upgrade, list)",
                    "Connect to Linux servers over SSH, using keys, and locate sshd/sshd_config",
                    "Troubleshoot SSH access failures using a gate-by-gate method including ~/.ssh permissions",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-019",
        "title": "Services, Logs, and Linux Troubleshooting",
        "description": "systemd, journalctl, failed-service diagnosis, network config, Linux DNS, cron. Week 19.",
        "target_role": "Junior Systems Technician",
        "difficulty_band": 4,
        "estimated_hours": 16,
        "module_order": 20,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "systemd Services and journalctl",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "systemd runs and supervises services (daemons) on modern Linux — the equivalent of "
                    "Windows Services, and the heart of most Linux tickets. The commands you'll use every "
                    "day (systemctl):\n"
                    "- systemctl status <service> — is it running? failed? enabled at boot? Shows the last "
                    "few log lines RIGHT THERE (your first evidence).\n"
                    "- systemctl start/stop/restart <service> — control it.\n"
                    "- systemctl enable/disable <service> — whether it starts at boot (enabled ≠ running; "
                    "a service can be enabled but currently stopped, or running but not enabled — a "
                    "'works until reboot' trap).\n"
                    "- systemctl list-units --failed — every failed service at a glance.\n\n"
                    "journalctl — the system log reader (the Event Viewer of systemd):\n"
                    "- journalctl -u <service> — logs for one service.\n"
                    "- journalctl -u <service> -e — jump to the newest entries.\n"
                    "- journalctl -f — follow live (like tail -f).\n"
                    "- journalctl --since '10 min ago' — time-bounded.\n\n"
                    "THE FAILED-SERVICE INVESTIGATION (the Linux ticket workhorse):\n"
                    "1. systemctl status <service> — confirm it's failed; read the summary + last lines.\n"
                    "2. journalctl -u <service> -e — read the ACTUAL error (config typo? missing file? "
                    "port in use? permission denied?). The first error in the chain, as always.\n"
                    "3. Fix the specific cause (often a config error in /etc/... or a permission).\n"
                    "4. systemctl restart <service>; status to confirm active; verify the thing it "
                    "provides actually works.\n"
                    "5. If it should survive reboot, ensure it's enabled.\n\n"
                    "COMMON MISTAKES: restarting blindly without reading journalctl (it fails again for "
                    "the same reason); confusing enabled with running; declaring success on 'active' "
                    "without verifying the service actually does its job; not checking the config file the "
                    "error names."
                ),
                "outcomes": [
                    "Control and inspect services with systemctl (status, start/stop/restart, enable/disable, --failed)",
                    "Read service logs with journalctl (-u, -e, -f, --since) to find the real error",
                    "Run the failed-service investigation from status through verified recovery",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Linux Networking and DNS Troubleshooting",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "Everything you learned about IP, gateway, and DNS troubleshooting applies on Linux — "
                    "different commands, same reasoning.\n"
                    "- ip a (or ip addr) — the ipconfig of Linux: interfaces, IPs, and state (UP/DOWN).\n"
                    "- ip r (ip route) — the routing table and default gateway.\n"
                    "- ping — same as everywhere; ping the gateway, then an IP, then a name (the Week 8 "
                    "triage tree, on Linux).\n"
                    "- DNS: cat /etc/resolv.conf shows the configured resolvers; dig or nslookup queries "
                    "DNS (dig google.com, or dig @1.1.1.1 google.com to compare against a known resolver). "
                    "getent hosts <name> shows what the system actually resolves (respecting /etc/hosts "
                    "too).\n"
                    "- /etc/hosts — a local static name file that OVERRIDES DNS; a stale entry here is a "
                    "sneaky 'wrong IP for a name' cause.\n\n"
                    "CONFIG (Ubuntu netplan awareness): modern Ubuntu configures networking via netplan "
                    "YAML in /etc/netplan/. A junior reads it and recognizes a wrong static IP/gateway/DNS "
                    "there; applying changes is netplan apply. (Recognize it; heavy edits often escalate.)\n\n"
                    "THE LINUX 'CAN'T REACH X' TRIAGE: ip a (do I have a valid address?) → ip r (is there a "
                    "default gateway?) → ping gateway → ping 1.1.1.1 → dig a name (DNS?). Compare configured "
                    "DNS vs a known resolver exactly as on Windows. 'ping by IP works, by name fails' is "
                    "still DNS; check /etc/resolv.conf and /etc/hosts.\n\n"
                    "COMMON MISTAKES: forgetting /etc/hosts can override DNS; editing netplan without "
                    "netplan apply; assuming the DNS SERVER is down when it's the client's resolv.conf; "
                    "not using the same layered triage you'd use on Windows."
                ),
                "outcomes": [
                    "Inspect Linux networking with ip a / ip r and apply the layered connectivity triage",
                    "Troubleshoot Linux DNS with resolv.conf, /etc/hosts, dig/getent, and known-resolver comparison",
                    "Recognize netplan configuration and when a network change is a read-and-escalate vs a safe fix",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Scheduled Jobs with cron",
                "lesson_order": 3,
                "estimated_minutes": 60,
                "summary": (
                    "cron runs jobs on a schedule — the Linux equivalent of Task Scheduler, behind most "
                    "'the nightly backup/report/cleanup didn't run' tickets.\n"
                    "- crontab -l lists a user's cron jobs; crontab -e edits them. System-wide jobs live "
                    "in /etc/crontab and /etc/cron.d/, and /etc/cron.daily etc.\n"
                    "- The five fields: minute, hour, day-of-month, month, day-of-week, then the command. "
                    "'0 2 * * * /path/script.sh' = 02:00 every day. You don't memorize exotic schedules — "
                    "you READ them to confirm when a job was supposed to run.\n\n"
                    "THE 'JOB DIDN'T RUN' INVESTIGATION:\n"
                    "1. Does the cron entry exist and is the schedule what you expect? (crontab -l / the "
                    "cron.d file.)\n"
                    "2. Did cron try to run it? Check logs (journalctl -u cron or /var/log/syslog for CRON "
                    "entries).\n"
                    "3. Did the job FAIL when it ran? cron emails output by default, or the script logs — "
                    "common causes: wrong path (cron has a minimal environment, so a script that works in "
                    "your shell fails under cron because a command isn't found), missing permissions, or "
                    "the script itself erroring.\n"
                    "4. Fix and verify by running the command manually AS the cron user, then confirming "
                    "the next scheduled run (or forcing a test).\n\n"
                    "THE CLASSIC GOTCHA: 'it works when I run it, but not from cron' = cron's minimal "
                    "environment/PATH. Use full paths in cron jobs. This is a frequently-tested real "
                    "scenario.\n\n"
                    "COMMON MISTAKES: assuming the schedule without reading it; not checking cron logs; "
                    "missing the environment/PATH difference; a script needing sudo that cron can't "
                    "provide; not verifying by running as the cron user."
                ),
                "outcomes": [
                    "Read and edit cron schedules (crontab -l/-e, the five fields, system cron locations)",
                    "Investigate a failed scheduled job through cron logs and the run-environment difference",
                    "Verify a fix by running the job as the cron user and confirming the schedule",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-020",
        "title": "Linux in Production: Web, Firewall, Backup, and Monitoring",
        "description": "nginx/apache admin, ufw, updates, backup/restore, resource triage, bash, monitoring/alert triage. Week 20.",
        "target_role": "Junior Systems Technician",
        "difficulty_band": 4,
        "estimated_hours": 17,
        "module_order": 21,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Web Server and Firewall Administration",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "WEB SERVER (nginx/apache) basics a junior supports:\n"
                    "- The service is nginx (or apache2) under systemd — so status/restart/journalctl are "
                    "exactly the Week 19 skills. 'The website is down' starts with systemctl status nginx.\n"
                    "- Config lives in /etc/nginx/ (sites-available / sites-enabled) or /etc/apache2/. A "
                    "config TYPO stops the service from starting — nginx -t TESTS the config before you "
                    "restart (always test before reload; a bad reload takes the site down). Recognize a "
                    "syntax error message and the file/line it points to.\n"
                    "- Logs: /var/log/nginx/access.log and error.log — the error log tells you WHY a page "
                    "fails (permissions on the web root, a missing file, an upstream app down).\n"
                    "- 'It runs but returns 403/404/502': 403 often web-root PERMISSIONS (the www-data "
                    "user can't read the files — a permissions ticket!), 404 wrong path/root, 502 the "
                    "backend app the web server proxies to is down.\n\n"
                    "FIREWALL (ufw): ufw status shows rules; ufw allow 80/tcp opens a port; ufw deny "
                    "closes. The Week 7 lesson holds: if a service is refused over the network but works "
                    "locally, check the firewall RULE — don't just disable ufw. 'Works on the server, "
                    "refused from outside' + a service that's clearly up = a missing allow rule.\n\n"
                    "THE TIE-BACK: a 'website down' ticket might be the service (systemctl), a config typo "
                    "(nginx -t), permissions on the web root (ls -l, the Week 18 skill), or the firewall "
                    "(ufw) — you now have a layered method for it.\n\n"
                    "COMMON MISTAKES: reloading nginx without nginx -t (bad config = outage); disabling "
                    "ufw instead of adding a rule; ignoring the error log; missing that a 403 is often a "
                    "web-root permission problem."
                ),
                "outcomes": [
                    "Support a web server via systemd, config-test (nginx -t), and the access/error logs",
                    "Interpret 403/404/502 as permissions, path, or backend problems and act accordingly",
                    "Manage ufw rules and diagnose 'refused from outside' without disabling the firewall",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Resource Triage, Backup, and Bash",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "RESOURCE TRIAGE — the Linux 'server is slow/full' toolkit:\n"
                    "- top (or htop) — live CPU/memory per process; find the hog (the Task Manager skill).\n"
                    "- df -h — disk space per filesystem ('disk full' truth); du -sh /path/* — what's "
                    "consuming a directory (the Windows disk-space lesson, Linux commands). The classic: "
                    "/var/log or an app log filling the disk — find it with du, fix the source.\n"
                    "- free -h — memory; a swap-thrashing box is slow for a reason you can see.\n"
                    "- ps aux — process snapshot; combine with grep to find a specific process.\n\n"
                    "BACKUP & RESTORE (Linux): tar for archives (tar -czf backup.tar.gz /path to create, "
                    "tar -xzf to extract), rsync for efficient copies/sync to another host or disk. The "
                    "principle from Week 17 is identical: an untested backup is a hope — RESTORE and VERIFY "
                    "(extract to a test location, confirm the files are intact and correct). Config backups "
                    "before editing /etc files are the everyday version.\n\n"
                    "BASH FUNDAMENTALS (technician level, not development): variables, running a script "
                    "(chmod +x script.sh; ./script.sh), the shebang (#!/bin/bash), simple if/for, and "
                    "reading someone else's script well enough to know what it does BEFORE you run it. "
                    "Piping and redirection (|, >, >>) you already use. A small script that, say, checks a "
                    "service and logs the result is the Linux version of the Week 17 PowerShell script — "
                    "small, commented, safe.\n\n"
                    "SAFETY: read scripts before running them (especially anything with rm, dd, or sudo); "
                    "test a restore in a scratch location; back up a config before editing.\n\n"
                    "COMMON MISTAKES: 'disk full' without du to find the cause; killing the wrong process; "
                    "never testing a tar/rsync restore; running an unread script; editing /etc with no "
                    "backup copy."
                ),
                "outcomes": [
                    "Triage CPU/memory/disk with top, df -h, du, free, and ps to find the actual cause",
                    "Create and VERIFY backups/restores with tar and rsync, and back up configs before edits",
                    "Read and write small, safe bash scripts and never run an unread script",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Monitoring and Alert Triage",
                "lesson_order": 3,
                "estimated_minutes": 75,
                "summary": (
                    "Monitoring is how you find problems BEFORE the user calls — and alert triage is a "
                    "daily operations skill. In this program, Netdata (real-time system metrics) and "
                    "Uptime Kuma (service/endpoint up-down checks) are the tools; the SKILLS transfer to "
                    "any monitoring stack.\n\n"
                    "READING METRICS: Netdata shows CPU, memory, disk I/O, disk space, network per host in "
                    "real time. You learn the NORMAL shape of a system so ABNORMAL stands out — a CPU "
                    "pinned at 100%, disk filling on a slope, memory exhausted. This is proactive triage: "
                    "'disk on FILES01 will be full in ~2 days at this rate' is a ticket you open before "
                    "the outage.\n\n"
                    "ALERT TRIAGE (the core operations loop): an alert fires ('service X down', 'disk "
                    ">90%'). The triage:\n"
                    "1. Is it REAL or noise? (A flapping check, a one-second blip, a known maintenance "
                    "window.) Not every alert is an incident.\n"
                    "2. Scope & impact: one host or many? user-facing? (Prioritization, Week 4/8, applied "
                    "to alerts.)\n"
                    "3. Correlate: does Netdata show WHY (disk full → service crashed → Uptime Kuma says "
                    "down)? Alerts are symptoms; find the cause.\n"
                    "4. Act or escalate with evidence: fix if in scope (clear the disk, restart the "
                    "service after finding why), or escalate with the metric graphs attached.\n"
                    "5. VERIFY the alert clears and note what happened.\n\n"
                    "ALERT FATIGUE is real: tuning out noisy alerts is dangerous; part of good ops is "
                    "flagging alerts that cry wolf so they get fixed, not ignored.\n\n"
                    "COMMON MISTAKES: treating every alert as a five-alarm fire (or ignoring all of them); "
                    "restarting the service the alert names without finding the cause (disk still full → "
                    "it crashes again); not correlating metrics; closing an alert without verifying it "
                    "actually cleared."
                ),
                "outcomes": [
                    "Read real-time metrics (Netdata) and up/down checks (Uptime Kuma) to spot problems proactively",
                    "Triage an alert: real-vs-noise, scope, correlate to cause, act or escalate with evidence",
                    "Verify an alert clears and recognize/flag alert fatigue rather than ignoring alerts",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]


QUIZZES_E = [
    {
        "title": "Linux Fundamentals: Files, Permissions, SSH",
        "week_number": 18, "domain_id": "6.0", "lesson_title": "Permissions, Users, Groups, and sudo",
        "questions": [
            _q("Which directory holds most Linux configuration files?",
               "/home", "/etc", "/var", "/usr",
               "B", "/etc is the standard location for system and service configuration."),
            _q("ls -l shows -rwxr-x---. The 'others' permission is:",
               "Read and execute", "Read and write", "No access", "Full access",
               "C", "Owner rwx, group r-x, others --- = 750; others get no access."),
            _q("To add a user to a group WITHOUT removing their existing groups, use:",
               "usermod -G group user (replaces groups)", "usermod -aG group user", "chmod group user", "chown user:group",
               "B", "The -a (append) is essential; usermod -G alone replaces all group memberships."),
            _q("chmod 777 on a web file to 'make it work' is bad because it:",
               "Makes file access slower", "Grants everyone full access",
               "Deletes the target file", "Requires an immediate system reboot",
               "B", "777 is the Linux equivalent of Full Control to Everyone."),
            _q("On a DIRECTORY, the execute (x) permission means:",
               "Run directory contents as a program", "Enter and traverse it", "Delete the directory", "No access at all",
               "B", "Directory x controls the ability to cd into and traverse the directory."),
            _q("You get 'Permission denied' editing a system file. The likely need (used carefully) is:",
               "Use chmod 777 on system files", "Use sudo for the command", "Restart the system", "Delete the file",
               "B", "System files require elevated rights; sudo runs the specific command as root, logged."),
            _q("Which commands help investigate a Linux 'access denied'? (select all that apply)",
               "ls -l on the file/directory", "id <user> to see group memberships", "chmod 777 immediately", "checking owner vs group vs other",
               "A", "Inspect perms, ownership, and group membership; 777 is a sledgehammer, not an investigation.", multi="A,B,D"),
            _q("SSH refuses your key with 'Permission denied (publickey)'. A classic cause is:",
               "The server is powered off or unreachable", "Bad .ssh permissions or key",
               "DNS lookup failure", "An allowed firewall rule",
               "B", "SSH ignores keys if ~/.ssh perms are too permissive, or if the public key isn't in authorized_keys."),
        ],
    },
    {
        "title": "Services, Logs, and Linux Networking",
        "week_number": 19, "domain_id": "6.0", "lesson_title": "systemd Services and journalctl",
        "questions": [
            _q("To see whether a service is running, failed, and enabled at boot, run:",
               "journalctl -f", "systemctl status <service>", "ps aux complete process listing", "top performance view",
               "B", "systemctl status gives state, enabled/disabled, and recent log lines."),
            _q("A service is 'enabled' but currently 'inactive (dead)'. This means:",
               "It is running normally", "It starts at boot, but is stopped",
               "It has been uninstalled", "It crashed permanently",
               "B", "enabled = starts at boot; it can still be stopped currently — a 'works after reboot' trap."),
            _q("To read the actual error a failed service produced:",
               "Ping the server", "journalctl -u <service> -e", "Change binary permissions", "Restart the entire server",
               "B", "journalctl -u <service> -e shows that service's newest log entries — the real error."),
            _q("Restarting a failed service without reading its logs typically results in:",
               "A permanent fix", "The same failure recurring",
               "Immediate data loss", "A full operating-system reboot",
               "B", "The root cause (config typo, missing file, port in use) remains; read journalctl first."),
            _q("The Linux equivalent of ipconfig (interfaces and IPs) is:",
               "ip a", "ls -l", "df -h", "top",
               "A", "ip a (ip addr) lists interfaces, addresses, and state."),
            _q("ping by IP works but by name fails on Linux. Check: (select all that apply)",
               "/etc/resolv.conf (configured DNS servers)", "/etc/hosts (may override with a stale entry)",
               "dig against a known resolver to compare", "the CPU temperature",
               "A", "resolv.conf, /etc/hosts, and a known-resolver comparison are the DNS checks.", multi="A,B,C"),
            _q("A cron job 'works when I run it manually but not from cron'. The classic cause is:",
               "The disk is full", "Cron lacks the interactive PATH",
               "DNS lookup failure", "The user account is locked",
               "B", "cron runs with a minimal environment; commands not in its PATH fail unless full paths are used."),
            _q("To confirm WHEN a cron job was scheduled to run, you:",
               "Guess from prior runs", "Read the five crontab fields", "Restart the cron service", "Check network firewall rules",
               "B", "The five fields (min hour dom mon dow) define the schedule — read them."),
        ],
    },
    {
        "title": "Linux in Production and Monitoring",
        "week_number": 20, "domain_id": "6.0", "lesson_title": "Monitoring and Alert Triage",
        "questions": [
            _q("Before reloading nginx after a config change, you should run:",
               "nginx -reboot", "nginx -t", "Disable the firewall", "Remove the configuration",
               "B", "nginx -t validates the config; reloading a broken config takes the site down."),
            _q("A working nginx returns 403 Forbidden on a page. A common cause is:",
               "DNS lookup failure", "Web-root permissions", "A full system disk", "Incorrect DNS record",
               "B", "403 is frequently a permissions problem on the web root — a Week 18 skill applied."),
            _q("A service works locally on the server but is 'refused' from outside. Check FIRST:",
               "Reinstall the operating system", "The firewall rule for that port",
               "Current CPU utilization", "DNS resolution settings",
               "B", "Refused-from-outside + up-locally points at a missing firewall allow rule."),
            _q("'Disk full' on Linux — the right way to find the cause is:",
               "Delete random files", "Measure with df and du",
               "Restart the server", "chmod 777 on root",
               "B", "Measure with df then du before deleting; often a runaway log in /var/log."),
            _q("An untested tar/rsync backup is:",
               "Perfectly safe", "Only a hope until restored",
               "Faster than a tested backup", "Automatically encrypted",
               "B", "Restore-and-verify is the point; the Week 17 lesson holds on Linux."),
            _q("An alert fires 'service X down'. A good first triage question is:",
               "Is it real, and what is affected?",
               "Who caused the outage?", "Should every service restart?", "Can the alert be ignored?",
               "A", "Real-vs-noise plus scope/impact comes before action; alerts are symptoms."),
            _q("An alert says disk >90% and the service crashed. Restarting only the service will:",
               "Fix it permanently", "Likely fail again while disk is full",
               "Free disk space", "Clear the alert forever",
               "B", "Address the cause (disk) or the symptom recurs; alerts are symptoms, not causes."),
            _q("Which tools are used for monitoring in this program? (select all that apply)",
               "Netdata (real-time metrics)", "Uptime Kuma (up/down checks)", "nginx", "cron",
               "A", "Netdata and Uptime Kuma are the monitoring tools; nginx and cron are services.", multi="A,B"),
        ],
    },
]


# Linux tickets — the PRIMARY assessment for Weeks 18-20 (master prompt Part 3).
TICKETS_E = [
    # ---------------- Week 18 ----------------
    {
        "title": "Linux: 'Permission denied' on the shared reports directory",
        "description": (
            "{{USER}} has an account on the Ubuntu file server LNX-FILES. They need to save reports into "
            "/srv/reports, which the whole {{TEAM}} team uses daily, but they get 'Permission denied' "
            "writing there — reading works. They were added to the team 'last week'. You have SSH and sudo "
            "on LNX-FILES."
        ),
        "difficulty": 3, "week_number": 18, "category": "Linux", "domain_id": "6.0",
        "root_cause": "/srv/reports is owned root:{{TEAM}} with 775; {{USER}} was never actually added to the {{TEAM}} group (or their session predates the add), so they fall into 'others' (r-x). Adding them to the group with usermod -aG and a fresh login fixes it",
        "root_cause_type": "linux_permissions",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Inspect the directory: ls -ld /srv/reports (owner, group, mode)", "required_mention": ["ls -l", "owner", "group", "775", "mode"], "weight": 0.3},
            {"id": 2, "step": "Check the user's groups: id {{USER}} — are they in {{TEAM}}?", "required_mention": ["id ", "groups", "member"], "weight": 0.3},
            {"id": 3, "step": "Fix at the group level: usermod -aG {{TEAM}} {{USER}} (the -a matters)", "required_mention": ["usermod", "-ag", "-aG", "append"], "weight": 0.25},
            {"id": 4, "step": "Fresh login (group takes effect), verify a write succeeds; NO chmod 777", "required_mention": ["log out", "new session", "verify", "write"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "ls -ld and id output before the fix", "validation": {}},
            {"type": "screenshot", "description": "Successful write to /srv/reports after re-login", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = perms/ownership and group membership inspected before any change",
            "2 = missing {{TEAM}} group membership identified (not 'the folder is broken')",
            "2 = usermod -aG used (append!); chmod 777 or changing the dir's perms/owner = 0-1",
            "2 = write verified in a fresh session; read/write confirmed working for the user",
            "2 = user told plainly it was a group-membership gap; note records the change",
        ),
        "model_answer": (
            "ls -ld /srv/reports: root:{{TEAM}} 775 — group members write, others read-only. id {{USER}}: "
            "not in {{TEAM}}. The onboarding add was missed. sudo usermod -aG {{TEAM}} {{USER}} (the -a "
            "prevents wiping their other groups). Have them start a fresh SSH session (group membership "
            "applies at login — the Linux token-refresh), then verify: touch /srv/reports/test-{{USER}} "
            "succeeds. Do NOT chmod the directory — the perms are correct; the membership was the gap."
        ),
        "hints": [
            "Reading works, writing doesn't. Look at WHO can write that directory and HOW your user is classified.",
            "ls -ld /srv/reports and id {{USER}} — compare the directory's group to the user's groups.",
            "The user isn't in the directory's group, so they're 'others' (read-only). Fix the membership, not the directory.",
            "sudo usermod -aG {{TEAM}} {{USER}}, fresh login, verify a write. Never usermod -G without -a, and never chmod 777.",
        ],
        "parameters": {"placeholders": {
            "USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
            "TEAM": ["reports", "analytics", "ops", "finance", "audit"],
        }},
    },
    {
        "title": "Linux: locked out of SSH after 'tidying up' the .ssh folder",
        "description": (
            "{{USER}} manages the app server LNX-APP over SSH with key auth. After 'organizing their home "
            "directory' they now get 'Permission denied (publickey)' and cannot log in. Password auth is "
            "disabled on this server (by policy). You have sudo access via the server console (Proxmox/"
            "management access)."
        ),
        "difficulty": 3, "week_number": 18, "category": "Linux", "domain_id": "6.0",
        "root_cause": "The user's tidy-up changed ~/.ssh permissions/ownership (or moved authorized_keys); SSH refuses keys when ~/.ssh is too open or authorized_keys is wrong. Restoring perms (700 ~/.ssh, 600 authorized_keys, correct ownership) restores access without touching sshd policy",
        "root_cause_type": "ssh_lockout",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Check sshd is running and policy is unchanged (server-side fine)", "required_mention": ["sshd", "systemctl", "running", "policy"], "weight": 0.2},
            {"id": 2, "step": "Inspect ~/.ssh: ls -la — permissions, ownership, authorized_keys present?", "required_mention": ["ls -la", ".ssh", "authorized_keys", "permissions"], "weight": 0.3},
            {"id": 3, "step": "Restore: 700 on ~/.ssh, 600 on authorized_keys, correct owner; keys content intact", "required_mention": ["700", "600", "chmod", "chown"], "weight": 0.3},
            {"id": 4, "step": "Verify SSH key login works; do NOT enable password auth as a workaround", "required_mention": ["verify", "log in", "key", "no password auth"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "ls -la ~/.ssh before and after the fix", "validation": {}},
            {"type": "screenshot", "description": "Successful key-based SSH login", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = server-side ruled in/out first, then the user's ~/.ssh inspected — 'tidying' clue used",
            "2 = wrong ~/.ssh perms/ownership (or displaced authorized_keys) identified as the refusal cause",
            "2 = perms restored precisely (700/600, ownership); enabling password auth or editing sshd policy = 0-1",
            "2 = key login verified end-to-end",
            "2 = user shown WHY ssh is picky about those permissions, kindly",
        ),
        "model_answer": (
            "systemctl status sshd: running; policy unchanged — other users unaffected, so it's this "
            "account. From console: ls -la /home/{{USER}}/.ssh — the tidy-up left .ssh at 755/wrong owner "
            "(or authorized_keys moved/renamed). SSH deliberately refuses keys in that state. Restore: "
            "chown -R {{USER}}:{{USER}} ~/.ssh; chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys; "
            "confirm the public key content is intact. Verify a fresh key login. Do not enable password "
            "auth 'temporarily' — that's a policy violation dressed as a favor."
        ),
        "hints": [
            "The error names the auth method. What did the 'tidying' most likely touch?",
            "From the console, ls -la the user's .ssh directory. SSH is strict about something you can see there.",
            "SSH refuses keys when ~/.ssh or authorized_keys permissions/ownership are wrong.",
            "chown the user's ~/.ssh back, chmod 700 on .ssh and 600 on authorized_keys, verify key login. Don't 'fix' it by enabling password auth.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"]}},
    },
    # ---------------- Week 19 ----------------
    {
        "title": "Linux: internal wiki down after last night's maintenance",
        "description": (
            "The team wiki on LNX-WIKI (nginx front end) is down this morning — browsers get 'connection "
            "refused'. Last night {{ADMIN}} 'applied some config cleanups' before leaving. The VM is up "
            "and reachable (ping works). You have SSH and sudo."
        ),
        "difficulty": 3, "week_number": 19, "category": "Linux", "domain_id": "6.0",
        "root_cause": "The cleanup introduced a typo in an nginx config include; nginx failed to start on its nightly restart. journalctl/nginx -t point at the exact file:line. Fixing the typo, testing with nginx -t, and starting the service restores the wiki",
        "root_cause_type": "failed_service_config",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "systemctl status nginx — confirm failed and read the summary", "required_mention": ["systemctl status", "failed", "nginx"], "weight": 0.25},
            {"id": 2, "step": "Read the real error: journalctl -u nginx -e and/or nginx -t (file:line)", "required_mention": ["journalctl", "nginx -t", "error", "line"], "weight": 0.3},
            {"id": 3, "step": "Fix the specific config typo (backup the file first), re-test with nginx -t", "required_mention": ["fix", "typo", "backup", "nginx -t"], "weight": 0.25},
            {"id": 4, "step": "Start/enable service, verify the wiki loads; note cause for {{ADMIN}}", "required_mention": ["start", "verify", "loads", "note"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "The failing status + the error naming file:line", "validation": {}},
            {"type": "screenshot", "description": "nginx -t passing and the wiki loading", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = status → journalctl/nginx -t read BEFORE changing anything; last-night clue used",
            "2 = the specific config error (file and line) identified",
            "2 = targeted fix with a config backup; nginx -t BEFORE restart; blind restarts = 1",
            "2 = service active AND the wiki actually loads in a browser",
            "2 = professional note to/about {{ADMIN}}'s change without blame; cause documented",
        ),
        "model_answer": (
            "systemctl status nginx: failed. journalctl -u nginx -e (or nginx -t) names the broken "
            "include and line from last night's cleanup. cp the file to a .bak, fix the typo, nginx -t "
            "until it passes, systemctl start nginx, confirm enabled, and load the wiki in a browser. "
            "Document the exact file/line and the maintenance change as the cause — factually, not "
            "blamefully."
        ),
        "hints": [
            "'Connection refused' with the VM up usually means the SERVICE isn't listening. Check its status.",
            "The service failed. Don't restart blindly — read WHY: journalctl -u nginx -e.",
            "There's a config test command that names the exact broken file and line.",
            "nginx -t points at the typo from last night. Back the file up, fix it, nginx -t clean, start the service, and verify the wiki loads.",
        ],
        "parameters": {"placeholders": {"ADMIN": ["the on-call admin", "jmorales", "the previous shift", "the contractor", "srivera"]}},
    },
    {
        "title": "Linux: nightly cleanup job silently stopped running",
        "description": (
            "The nightly cleanup script on LNX-APP (/opt/scripts/cleanup.sh, scheduled 02:00 via cron) "
            "hasn't produced its usual log entries for {{DAYS}} days — discovered when old temp data "
            "started piling up. The script runs fine when {{USER}} executes it manually. You have SSH and "
            "sudo."
        ),
        "difficulty": 4, "week_number": 19, "category": "Linux", "domain_id": "6.0",
        "root_cause": "A recent edit changed the script to call a command by bare name that isn't in cron's minimal PATH (works in an interactive shell, fails under cron). Cron logs show the runs; the script errors 'command not found'. Using full paths in the script fixes it",
        "root_cause_type": "cron_environment",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Confirm the schedule exists (crontab -l / cron.d) and matches 02:00", "required_mention": ["crontab", "schedule", "02:00", "cron.d"], "weight": 0.2},
            {"id": 2, "step": "Check whether cron RAN it: journalctl -u cron / syslog CRON entries", "required_mention": ["journalctl", "syslog", "cron", "ran"], "weight": 0.3},
            {"id": 3, "step": "Find the failure: command not found under cron's minimal PATH; ties to 'works manually'", "required_mention": ["command not found", "path", "environment", "manual"], "weight": 0.3},
            {"id": 4, "step": "Fix with full paths, test AS the cron context, verify next run / forced run", "required_mention": ["full path", "test", "verify", "run"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Cron log entries showing the job ran + the script's error", "validation": {}},
            {"type": "screenshot", "description": "A successful run after the fix (log output present)", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = schedule verified, cron logs checked — established cron RAN it before blaming cron",
            "2 = minimal-PATH/environment cause identified and tied to the works-manually clue",
            "2 = full paths in the script (or PATH set in the crontab); re-scheduling or 'run it manually daily' = 0-1",
            "2 = verified via a real (or forced) run producing the expected log output",
            "2 = note explains the interactive-vs-cron environment difference for the team",
        ),
        "model_answer": (
            "crontab -l: the 02:00 entry exists. journalctl (or /var/log/syslog) shows CRON executing it "
            "nightly — so cron is fine; the SCRIPT fails. Its output/log shows 'command not found' for a "
            "tool referenced by bare name after a recent edit: present in an interactive PATH, absent in "
            "cron's minimal one — exactly why it 'works manually'. Fix: full paths in the script (or set "
            "PATH in the crontab). Test in a cron-like context (env -i or force a run), confirm the log "
            "entries return, and note the environment lesson."
        ),
        "hints": [
            "'Works manually but not on schedule' is a famous pattern. First: did cron even TRY to run it?",
            "Cron logs (journalctl -u cron or syslog) will show the 02:00 executions. So what failed — cron, or the script under cron?",
            "Cron's environment is minimal. What does the script call that an interactive shell finds but cron can't?",
            "A bare command name isn't in cron's PATH. Use full paths in the script (or set PATH in the crontab), force a test run, and verify the log output returns.",
        ],
        "parameters": {"placeholders": {
            "USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
            "DAYS": ["6", "4", "9", "5", "11"],
        }},
    },
    # ---------------- Week 20 ----------------
    {
        "title": "Linux: app server disk at 96% and climbing",
        "description": (
            "Uptime Kuma flagged LNX-APP degraded; Netdata shows the root filesystem at 96% and climbing "
            "steadily. The app team says 'we didn't change anything'. If the disk fills, the {{APP}} "
            "service (and its database writes) fail hard. You have SSH and sudo. Business hours — the "
            "service must stay up."
        ),
        "difficulty": 4, "week_number": 20, "category": "Linux", "domain_id": "6.0",
        "root_cause": "{{APP}}'s log at /var/log/{{APP}}/debug.log has grown to tens of GB — debug logging was left enabled after an incident weeks ago. Safe space recovery plus disabling debug logging (and log rotation) fixes cause and symptom; deleting unknown files or restarting blind risks the service",
        "root_cause_type": "disk_full_runaway_log",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Measure: df -h confirms, du -sh narrows to /var/log/{{APP}} (find the writer, don't guess)", "required_mention": ["df -h", "du", "/var/log", "measure"], "weight": 0.3},
            {"id": 2, "step": "Identify the runaway debug.log and WHY (debug logging left on)", "required_mention": ["debug", "log", "growing", "left on"], "weight": 0.25},
            {"id": 3, "step": "Safe recovery during business hours: truncate/compress the log (not rm on an open file blindly), disable debug, add rotation", "required_mention": ["truncate", "rotate", "logrotate", "disable debug", "safe"], "weight": 0.3},
            {"id": 4, "step": "Verify: df -h down, Netdata slope flat, alert cleared, service unaffected", "required_mention": ["verify", "df", "alert", "cleared", "netdata"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "df -h + du output identifying the log before the fix", "validation": {}},
            {"type": "screenshot", "description": "Recovered space and the flattened growth (df/Netdata) after", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = measured with df/du to the exact file; growth slope + monitoring evidence used",
            "2 = runaway debug log AND its cause (debug left enabled) identified — not just 'big file'",
            "2 = business-hours-safe recovery (truncate/compress + disable debug + rotation); rm -rf of unknowns or a casual service restart = 0-1",
            "2 = space verified recovered, growth stopped, alert cleared, service continuously up",
            "2 = app team informed factually; rotation recommended so it can't recur",
        ),
        "model_answer": (
            "df -h confirms 96%; du -sh /var/* → /var/log/{{APP}}/debug.log is tens of GB, timestamps "
            "show constant writes: debug logging left on after an old incident. Business-hours-safe fix: "
            "truncate the open log (truncate -s 0, or copy-then-truncate — NOT rm while the process holds "
            "it, which frees nothing until restart), disable debug logging per the app's config (or "
            "escalate that one setting to the app team), and add a logrotate rule. Verify df -h drops, "
            "Netdata slope flattens, the Kuma alert clears, and the service never blipped."
        ),
        "hints": [
            "96% and CLIMBING means something is writing right now. Measure — df -h, then du to walk down to it.",
            "The biggest, fastest-growing thing lives under /var/log. Which file, and why is it growing?",
            "Debug logging was left on. And careful: rm on a file a running process holds open frees nothing.",
            "Truncate the open debug log safely, turn debug logging off (or escalate that setting), add logrotate, then verify df drops, the Netdata slope flattens, and the alert clears — all without bouncing the service.",
        ],
        "parameters": {"placeholders": {"APP": ["invoicer", "ordersync", "timetrack", "docstore", "fleetview"]}},
    },
    {
        "title": "Linux: 'the website is broken from outside but fine on the server'",
        "description": (
            "After LNX-WEB was rebuilt on a fresh Ubuntu VM yesterday, the {{SITE}} site loads fine with "
            "curl on the server itself, but from any other machine browsers get 'connection refused' on "
            "port 443. nginx is active. The old VM 'just worked'. You have SSH and sudo."
        ),
        "difficulty": 3, "week_number": 20, "category": "Linux", "domain_id": "6.0",
        "root_cause": "The rebuilt VM's ufw is enabled with default deny and only OpenSSH allowed — nobody re-added the 80/443 allow rules. Adding the rules (not disabling ufw) restores outside access",
        "root_cause_type": "firewall_rule_missing",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Split local-vs-remote: curl on-server works + nginx active = service fine; path blocked", "required_mention": ["curl", "local", "remote", "active"], "weight": 0.3},
            {"id": 2, "step": "Check the firewall: ufw status — what's allowed on this rebuilt VM?", "required_mention": ["ufw status", "firewall", "allow"], "weight": 0.3},
            {"id": 3, "step": "Add the specific rules: ufw allow 80/tcp and 443/tcp — do NOT disable ufw", "required_mention": ["ufw allow", "443", "80", "not disable"], "weight": 0.25},
            {"id": 4, "step": "Verify from an OUTSIDE machine; note the rebuild-checklist gap", "required_mention": ["verify", "outside", "browser", "checklist"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "ufw status before (missing rules) and after", "validation": {}},
            {"type": "screenshot", "description": "The site loading from a remote machine", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = local-vs-remote test done deliberately; rebuild clue connected",
            "2 = missing ufw allow rules on the fresh VM identified",
            "2 = precise allow rules added; disabling ufw = 0",
            "2 = verified from a genuinely remote machine, not just on-server",
            "2 = rebuild-checklist gap flagged so the next rebuild includes firewall rules",
        ),
        "model_answer": (
            "Works locally + nginx active = the service is fine; the network path is blocked. On a fresh "
            "VM the prime suspect is the firewall: ufw status shows default deny with only OpenSSH "
            "allowed — the rebuild never re-added web rules. sudo ufw allow 80/tcp && sudo ufw allow "
            "443/tcp. Verify from an outside machine. Flag the rebuild checklist so firewall rules are "
            "part of every rebuild — this is a process fix, not just a ticket fix."
        ),
        "hints": [
            "It works ON the server but not from outside. What sits between outside clients and a listening service?",
            "The VM was REBUILT yesterday. What per-host protection starts fresh on a new build?",
            "ufw status — what's actually allowed in?",
            "Add ufw allow 80/tcp and 443/tcp (never disable ufw), verify from a remote machine, and get the firewall step added to the rebuild checklist.",
        ],
        "parameters": {"placeholders": {"SITE": ["intranet", "docs portal", "booking", "status page", "wiki"]}},
    },
]


def seed_phase_e(db) -> dict:
    """Idempotent Phase E seed — modules, lessons, quizzes, Linux tickets."""
    from app.models.learning import Lesson, Module
    from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz
    from app.models.ticket import Ticket
    from app.services.seed_question_sync import sync_seed_questions

    counts = {"modules": 0, "lessons": 0, "quizzes": 0, "questions": 0, "tickets": 0}
    prev_module = db.query(Module).filter(Module.code == "MOD-017").first()
    for spec in MODULES_E:
        module = db.query(Module).filter(Module.code == spec["code"]).first()
        fields = {k: spec[k] for k in ("title", "description", "target_role",
                  "difficulty_band", "estimated_hours", "module_order", "unlock_threshold")}
        if module is None:
            module = Module(code=spec["code"], **fields)
            db.add(module)
            counts["modules"] += 1
        else:
            for k, v in fields.items():
                setattr(module, k, v)
        if prev_module is not None:
            module.prerequisite_module_id = prev_module.id if module.id != prev_module.id else None
        db.flush()
        for lspec in spec["lessons"]:
            lesson = (db.query(Lesson)
                      .filter(Lesson.module_id == module.id,
                              Lesson.lesson_order == lspec["lesson_order"]).first())
            lfields = {k: lspec[k] for k in ("title", "summary", "outcomes",
                       "estimated_minutes", "required_notes_template", "status")}
            if lesson is None:
                db.add(Lesson(module_id=module.id, lesson_order=lspec["lesson_order"], **lfields))
                counts["lessons"] += 1
            else:
                for k, v in lfields.items():
                    setattr(lesson, k, v)
        db.flush()
        prev_module = module

    for qspec in QUIZZES_E:
        quiz = db.query(Quiz).filter(Quiz.title == qspec["title"]).first()
        lesson = db.query(Lesson).filter(Lesson.title == qspec["lesson_title"]).first()
        if quiz is None:
            quiz = Quiz(title=qspec["title"], week_number=qspec["week_number"],
                        domain_id=qspec["domain_id"], question_count=len(qspec["questions"]),
                        status=QUIZ_STATUS_PUBLISHED, lesson_id=lesson.id if lesson else None)
            db.add(quiz)
            counts["quizzes"] += 1
            db.flush()
        else:
            quiz.week_number = qspec["week_number"]
            quiz.domain_id = qspec["domain_id"]
            quiz.question_count = len(qspec["questions"])
            quiz.status = QUIZ_STATUS_PUBLISHED
            quiz.lesson_id = lesson.id if lesson else quiz.lesson_id
        counts["questions"] += sync_seed_questions(db, quiz, qspec["questions"])
        db.flush()

    for tspec in TICKETS_E:
        ticket = db.query(Ticket).filter(Ticket.title == tspec["title"]).first()
        if ticket is None:
            db.add(Ticket(**tspec))
            counts["tickets"] += 1
        else:
            for k, v in tspec.items():
                setattr(ticket, k, v)
    db.flush()
    return counts
