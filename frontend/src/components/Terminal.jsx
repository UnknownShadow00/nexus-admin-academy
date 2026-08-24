import { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";

function normalizeCommand(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

export function resolveCaseCommand(caseProfile, commandValue) {
  const command = normalizeCommand(commandValue);
  if (command === "help" || command === "get-help" || !command) {
    return {
      recognized: true,
      inspectionId: null,
      output: [
        "Suggested tool categories for this case:",
        ...(caseProfile?.help_topics || []).map((topic) => `  - ${topic}`),
        "Choose a relevant command; no required sequence is shown.",
      ],
    };
  }
  const configured = (caseProfile?.commands || []).find((item) =>
    [item.command, ...(item.aliases || [])].some((candidate) => normalizeCommand(candidate) === command),
  );
  if (!configured) {
    return {
      recognized: false,
      inspectionId: null,
      output: ["That command is unavailable in this focused case. Use help to review tool categories."],
    };
  }
  return {
    recognized: true,
    inspectionId: configured.inspection_id || null,
    output: configured.output || [],
  };
}

function processCommand(cmd, term, profile = "windows", caseProfile = null) {
  const command = cmd.trim().toLowerCase();

  if (caseProfile) {
    if (command === "cls" || command === "clear") {
      term.clear();
      term.writeln("");
      return { recognized: true, inspectionId: null, output: [] };
    }
    const result = resolveCaseCommand(caseProfile, command);
    result.output.forEach((line) => term.writeln(line));
    term.writeln("");
    return result;
  }

  if (command === "ipconfig" || command === "ipconfig /all") {
    term.writeln("Windows IP Configuration");
    term.writeln("");
    term.writeln("Ethernet adapter Ethernet:");
    term.writeln("   IPv4 Address. . . . . . . . . . . : 192.168.1.100");
    term.writeln("   Subnet Mask . . . . . . . . . . . : 255.255.255.0");
    term.writeln("   Default Gateway . . . . . . . . . : 192.168.1.1");
    if (command === "ipconfig /all") {
      term.writeln("   DHCP Enabled. . . . . . . . . . . : Yes");
      term.writeln("   DNS Servers . . . . . . . . . . . : 10.20.0.10");
    }
  } else if (command.startsWith("ping ")) {
    const target = command.split(" ")[1] || "unknown";
    term.writeln(`Pinging ${target} with 32 bytes of data:`);
    term.writeln(`Reply from ${target}: bytes=32 time=10ms TTL=64`);
    term.writeln(`Reply from ${target}: bytes=32 time=12ms TTL=64`);
    term.writeln(`Reply from ${target}: bytes=32 time=9ms TTL=64`);
    term.writeln(`Reply from ${target}: bytes=32 time=11ms TTL=64`);
  } else if (command === "get-service") {
    term.writeln("Status   Name               DisplayName");
    term.writeln("------   ----               -----------");
    term.writeln("Running  Dhcp               DHCP Client");
    term.writeln("Running  Dnscache           DNS Client");
    term.writeln("Stopped  Spooler            Print Spooler");
    term.writeln("Running  W32Time            Windows Time");
  } else if (command === "get-command") {
    term.writeln("CommandType  Name             Version  Source");
    term.writeln("-----------  ----             -------  ------");
    term.writeln("Cmdlet       Get-Service      7.4.0.0  Microsoft.PowerShell.Management");
    term.writeln("Cmdlet       Get-Help         7.4.0.0  Microsoft.PowerShell.Core");
    term.writeln("Cmdlet       Get-Member       7.4.0.0  Microsoft.PowerShell.Utility");
  } else if (command === "get-help" || command.startsWith("get-help ")) {
    const topic = cmd.trim().split(/\s+/).slice(1).join(" ") || "Get-Help";
    term.writeln(`NAME`);
    term.writeln(`    ${topic}`);
    term.writeln("SYNOPSIS");
    term.writeln("    Displays command help, syntax, parameters, and examples.");
  } else if (command === "get-process") {
    term.writeln("Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id  ProcessName");
    term.writeln("-------  ------    -----      -----     ------     --  -----------");
    term.writeln("    156      12     2548      12456       0.50   1234  chrome");
    term.writeln("     89       8     1824       8932       2.30   5678  explorer");
    term.writeln("     45       5      956       4512       0.10   9012  notepad");
  } else if (command === "ls" || command.startsWith("ls ")) {
    term.writeln("total 48");
    term.writeln("drwxr-xr-x  2 root root 4096 Jan 14 09:23 etc");
    term.writeln("-rw-r--r--  1 root root  220 Jan 14 09:23 .bash_logout");
    term.writeln("-rw-r--r--  1 root root 3526 Jan 14 09:23 .bashrc");
    term.writeln("drwxr-xr-x  3 root root 4096 Jan 14 09:23 var");
  } else if (command === "pwd") {
    term.writeln(profile === "linux" ? "/home/student01" : "C:\\Users\\Student");
  } else if (command.startsWith("cd ")) {
    const dir = command.split(" ")[1] || "~";
    term.writeln(`Changed directory to ${dir}`);
  } else if (command === "whoami") {
    term.writeln(profile === "linux" ? "student01" : "NEXUS\\student01");
  } else if (command === "hostname") {
    term.writeln("NX-WS-101");
  } else if (command === "systeminfo") {
    term.writeln("Host Name:                 NX-WS-101");
    term.writeln("OS Name:                   Microsoft Windows 11 Enterprise");
    term.writeln("System Type:               x64-based PC");
  } else if (command === "gpresult /r" || command === "gpresult") {
    term.writeln("COMPUTER SETTINGS");
    term.writeln("    Applied Group Policy Objects");
    term.writeln("        Nexus Workstation Baseline");
    term.writeln("USER SETTINGS");
    term.writeln("    Applied Group Policy Objects");
    term.writeln("        Nexus Standard User Policy");
  } else if (command === "gpupdate /force" || command === "gpupdate") {
    term.writeln("Updating policy...");
    term.writeln("Computer Policy update has completed successfully.");
    term.writeln("User Policy update has completed successfully.");
  } else if (command === "id") {
    term.writeln("uid=1001(student01) gid=1001(student01) groups=1001(student01),27(sudo)");
  } else if (command === "ip a" || command === "ip addr") {
    term.writeln("2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP");
    term.writeln("    inet 192.168.1.50/24 brd 192.168.1.255 scope global eth0");
  } else if (command === "ip r" || command === "ip route") {
    term.writeln("default via 192.168.1.1 dev eth0");
    term.writeln("192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.50");
  } else if (command === "crontab -l") {
    term.writeln("0 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1");
  } else if (command === "uptime") {
    term.writeln(" 14:32:10 up 3 days,  4:21,  2 users,  load average: 0.12, 0.08, 0.05");
  } else if (command === "free" || command.startsWith("free ")) {
    term.writeln("              total        used        free");
    term.writeln("Mem:        16384000     5234688    11149312");
    term.writeln("Swap:        2097152           0     2097152");
  } else if (command === "df" || command.startsWith("df ")) {
    term.writeln("Filesystem     1K-blocks    Used Available Use% Mounted on");
    term.writeln("/dev/sda1       51475068 8234092  40633584  17% /");
    term.writeln("tmpfs            8192000       0   8192000   0% /dev/shm");
  } else if (command.startsWith("du ")) {
    term.writeln("8.1G    /var/log");
    term.writeln("1.4G    /var/lib");
    term.writeln("240M    /var/cache");
  } else if (command === "ps" || command.startsWith("ps ")) {
    term.writeln("  PID TTY          TIME CMD");
    term.writeln(" 1234 pts/0    00:00:00 bash");
    term.writeln(" 5678 pts/0    00:00:01 python3");
    term.writeln(" 9012 pts/0    00:00:00 ps");
  } else if (command.startsWith("systemctl status")) {
    const svc = command.split(" ")[2] || "nginx";
    term.writeln(`● ${svc}.service - ${svc} service`);
    term.writeln(`   Loaded: loaded (/lib/systemd/system/${svc}.service; enabled)`);
    term.writeln("   Active: active (running) since Mon 2025-01-14 09:00:00 UTC; 5h ago");
    term.writeln("  Process: 1234 ExecStart=/usr/sbin/nginx (code=exited, status=0/SUCCESS)");
  } else if (command.startsWith("systemctl stop") || command.startsWith("systemctl start") || command.startsWith("systemctl restart")) {
    const parts = command.split(" ");
    term.writeln(`[  OK  ] ${parts[1]} ${parts[2] || "service"}.`);
  } else if (command === "netstat -ano" || command === "netstat") {
    term.writeln("Proto  Local Address          Foreign Address        State           PID");
    term.writeln("TCP    0.0.0.0:80             0.0.0.0:0              LISTENING       1234");
    term.writeln("TCP    0.0.0.0:443            0.0.0.0:0              LISTENING       1234");
    term.writeln("TCP    127.0.0.1:3306         0.0.0.0:0              LISTENING       5678");
    term.writeln("TCP    192.168.1.100:52341    8.8.8.8:443            ESTABLISHED     9012");
  } else if (command.startsWith("nslookup ")) {
    const host = command.split(" ")[1] || "example.com";
    term.writeln("Server:   8.8.8.8");
    term.writeln("Address:  8.8.8.8#53");
    term.writeln("");
    term.writeln("Non-authoritative answer:");
    term.writeln(`Name:   ${host}`);
    term.writeln("Address: 93.184.216.34");
  } else if (command.startsWith("tracert ")) {
    const host = command.split(" ")[1] || "example.com";
    term.writeln(`Tracing route to ${host} over a maximum of 30 hops`);
    term.writeln("  1    <1 ms    <1 ms    <1 ms  192.168.1.1");
    term.writeln("  2     8 ms     9 ms     8 ms  10.20.0.1");
    term.writeln(`  3    12 ms    11 ms    12 ms  ${host}`);
    term.writeln("Trace complete.");
  } else if (command.startsWith("dig ")) {
    const host = command.split(" ")[1] || "example.com";
    term.writeln(`; <<>> DiG 9.16.1-Ubuntu <<>> ${host}`);
    term.writeln(";; ANSWER SECTION:");
    term.writeln(`${host}.    3600    IN    A    93.184.216.34`);
  } else if (command === "arp -a" || command === "arp") {
    term.writeln("Interface: 192.168.1.100 --- 0x3");
    term.writeln("  Internet Address      Physical Address      Type");
    term.writeln("  192.168.1.1           00-14-22-01-23-45     dynamic");
    term.writeln("  192.168.1.255         ff-ff-ff-ff-ff-ff     static");
  } else if (command.startsWith("cat ")) {
    const file = command.split(" ")[1] || "file";
    term.writeln(`# Contents of ${file}`);
    term.writeln("[sample content would appear here]");
  } else if (command.startsWith("grep ")) {
    term.writeln("nexus_student01:x:1001:1001::/home/student01:/bin/bash");
  } else if (command.startsWith("find ")) {
    term.writeln("./var/log/syslog");
    term.writeln("./var/log/auth.log");
    term.writeln("./etc/nginx/nginx.conf");
  } else if (command.startsWith("ssh ")) {
    const target = command.split(" ")[1] || "server";
    term.writeln(`Connecting to ${target}...`);
    term.writeln(`Warning: Permanently added '${target}' (ECDSA) to the list of known hosts.`);
    term.writeln("Connected. (Simulated - no real connection)");
  } else if (command.startsWith("curl ") || command.startsWith("wget ")) {
    term.writeln("  % Total    % Received % Xferd  Average Speed");
    term.writeln("100  1256  100  1256    0     0   5234      0 --:--:-- --:--:--");
    term.writeln("Response: 200 OK");
  } else if (command === "ss" || command.startsWith("ss ")) {
    term.writeln("Netid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port");
    term.writeln("tcp    LISTEN  0       128     0.0.0.0:22           0.0.0.0:*");
    term.writeln("tcp    LISTEN  0       128     0.0.0.0:80           0.0.0.0:*");
  } else if (command === "last" || command.startsWith("last ")) {
    term.writeln("student01  pts/0   192.168.1.50   Mon Jan 14 09:00   still logged in");
    term.writeln("student01  pts/0   192.168.1.50   Sun Jan 13 18:30 - 20:15  (01:45)");
    term.writeln("reboot     system boot  Mon Jan 11 08:00");
  } else if (command.startsWith("tasklist")) {
    term.writeln("Image Name                     PID Session Name    Mem Usage");
    term.writeln("========================= ======== ================ ============");
    term.writeln("System Idle Process              0 Services            8 K");
    term.writeln("System                           4 Services          516 K");
    term.writeln("svchost.exe                   1234 Services        12,456 K");
    term.writeln("explorer.exe                  5678 Console         45,231 K");
  } else if (command.startsWith("sc query")) {
    const svc = command.split(" ")[2] || "wuauserv";
    term.writeln(`SERVICE_NAME: ${svc}`);
    term.writeln("        TYPE               : 20  WIN32_SHARE_PROCESS");
    term.writeln("        STATE              : 4  RUNNING");
    term.writeln("        WIN32_EXIT_CODE    : 0  (0x0)");
  } else if (command.startsWith("netsh")) {
    term.writeln("Windows IP Configuration");
    term.writeln("   DHCP Enabled. . . . . . . . . . . : Yes");
    term.writeln("   IP Address. . . . . . . . . . . . : 192.168.1.100");
    term.writeln("   Subnet Mask . . . . . . . . . . . : 255.255.255.0");
  } else if (command === "dmesg" || command.startsWith("dmesg")) {
    term.writeln("[    0.000000] Linux version 5.15.0-91-generic");
    term.writeln("[    0.000000] BIOS-provided physical RAM map");
    term.writeln("[    2.341234] eth0: renamed from veth3a2b1c");
    term.writeln("[   14.892341] systemd[1]: Reached target Network.");
  } else if (command === "journalctl" || command.startsWith("journalctl")) {
    term.writeln("Jan 14 09:00:01 server systemd[1]: Starting Session 1 of user student01.");
    term.writeln("Jan 14 09:00:02 server sshd[1234]: Accepted publickey for student01");
    term.writeln("Jan 14 09:15:33 server nginx[5678]: 192.168.1.50 - GET / HTTP/1.1 200");
  } else if (command === "nginx -t") {
    term.writeln("nginx: the configuration file /etc/nginx/nginx.conf syntax is ok");
    term.writeln("nginx: configuration file /etc/nginx/nginx.conf test is successful");
  } else if (command === "ufw status") {
    term.writeln("Status: active");
    term.writeln("To                         Action      From");
    term.writeln("22/tcp                     ALLOW       10.20.0.0/16");
    term.writeln("80/tcp                     ALLOW       Anywhere");
  } else if (command.startsWith("chmod ")) {
    term.writeln("Permissions updated.");
  } else if (command.startsWith("chown ")) {
    term.writeln("Ownership changed.");
  } else if (command.startsWith("mkdir ")) {
    const dir = command.split(" ")[1] || "newdir";
    term.writeln(`Directory '${dir}' created.`);
  } else if (command.startsWith("kill ")) {
    const pid = command.split(" ").pop();
    term.writeln(`Process ${pid} terminated.`);
  } else if (command.startsWith("sudo ")) {
    term.writeln("[sudo] password for student01:");
    term.writeln("Command executed with elevated privileges.");
  } else if (command === "cls" || command === "clear") {
    term.clear();
  } else if (!command || command === "help") {
    term.writeln("Available commands:");
    term.writeln("  ipconfig /all, ping [host], tracert [host], nslookup [host], netstat, arp");
    term.writeln("  hostname, systeminfo, whoami, gpresult /r, gpupdate /force");
    term.writeln("  get-command, get-help [command], get-service, get-process");
    term.writeln("  ls, pwd, cd, whoami, id, ip a, ip r, uptime, free, df, du, ps");
    term.writeln("  find, grep, cat, crontab -l, nginx -t, ufw status");
    term.writeln("  tasklist, sc query <service>, netsh, dmesg, journalctl, ssh, curl, wget");
    term.writeln("  systemctl status/start/stop/restart <service>, chmod, chown, mkdir, kill");
    term.writeln("  cls/clear");
  } else {
    term.writeln(`'${cmd}' is not recognized as a command.`);
    term.writeln("Type help for available commands.");
  }
  term.writeln("");
}

export default function TerminalWidget({ prefillCommand, onSessionChange, onCommandResult, profile = "windows", caseProfile = null, compact = false }) {
  const terminalRef = useRef(null);
  const termRef = useRef(null);
  const currentLineRef = useRef("");
  const historyRef = useRef([]);
  const historyIndexRef = useRef(-1);
  const sessionLinesRef = useRef([]);
  const onSessionChangeRef = useRef(onSessionChange);
  const onCommandResultRef = useRef(onCommandResult);

  useEffect(() => {
    onSessionChangeRef.current = onSessionChange;
  }, [onSessionChange]);

  useEffect(() => {
    onCommandResultRef.current = onCommandResult;
  }, [onCommandResult]);

  const clearCurrentLine = (term) => {
    for (let i = 0; i < currentLineRef.current.length; i += 1) {
      term.write("\b \b");
    }
    currentLineRef.current = "";
  };

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "Consolas, monospace",
      theme: { background: "#1e1e1e", foreground: "#ffffff" },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    const initialFitTimer = window.setTimeout(() => {
      try {
        fitAddon.fit();
      } catch {
        // no-op
      }
    }, 0);

    termRef.current = term;

    const isLinux = profile === "linux";
    const prompt = caseProfile?.prompt || (isLinux ? "student01@nexus:~$ " : "PS C:\\Users\\Student> ");

    const writePrompt = () => term.write(prompt);

    term.writeln(caseProfile ? "Focused Evidence Terminal" : isLinux ? "Linux Shell Practice Terminal" : "Windows PowerShell Practice Terminal");
    term.writeln(caseProfile?.intro || "Type commands to practice (simulated environment)");
    term.writeln(caseProfile ? "Type help for tool categories" : "Type help for command list");
    term.writeln("");
    writePrompt();

    term.onData((data) => {
      if (data === "\r") {
        term.write("\r\n");
        const command = currentLineRef.current;
        if (command.trim()) {
          historyRef.current.push(command);
          historyIndexRef.current = -1;
        }
        sessionLinesRef.current.push(`${prompt}${command}`);
        const result = processCommand(command, term, profile, caseProfile);
        sessionLinesRef.current.push("");
        currentLineRef.current = "";
        writePrompt();
        onSessionChangeRef.current?.(sessionLinesRef.current.join("\n"));
        onCommandResultRef.current?.({ command, ...(result || {}) });
      } else if (data === "\u0003") {
        term.write("^C\r\n");
        currentLineRef.current = "";
        historyIndexRef.current = -1;
        writePrompt();
      } else if (data === "\u007f") {
        if (currentLineRef.current.length > 0) {
          currentLineRef.current = currentLineRef.current.slice(0, -1);
          term.write("\b \b");
        }
      } else if (data === "\u001b[A") {
        if (historyRef.current.length > 0) {
          historyIndexRef.current = Math.min(historyIndexRef.current + 1, historyRef.current.length - 1);
          const prev = historyRef.current[historyRef.current.length - 1 - historyIndexRef.current];
          clearCurrentLine(term);
          currentLineRef.current = prev;
          term.write(prev);
        }
      } else if (data === "\u001b[B") {
        if (historyIndexRef.current > 0) {
          historyIndexRef.current -= 1;
          const next = historyRef.current[historyRef.current.length - 1 - historyIndexRef.current];
          clearCurrentLine(term);
          currentLineRef.current = next;
          term.write(next);
        } else {
          historyIndexRef.current = -1;
          clearCurrentLine(term);
        }
      } else {
        currentLineRef.current += data;
        term.write(data);
      }
    });

    const onResize = () => {
      try {
        fitAddon.fit();
      } catch {
        // no-op
      }
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      window.clearTimeout(initialFitTimer);
      termRef.current = null;
      term.dispose();
    };
  }, [caseProfile, profile]);

  useEffect(() => {
    if (!prefillCommand || !termRef.current) return;
    const term = termRef.current;
    clearCurrentLine(term);
    currentLineRef.current = prefillCommand;
    term.write(prefillCommand);
  }, [prefillCommand]);

  return (
    <div className="min-w-0 overflow-hidden rounded-lg border border-slate-300 bg-white p-4 shadow dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">{caseProfile ? "Focused case terminal" : "Practice Terminal"}</div>
      <div ref={terminalRef} style={{ height: compact ? "280px" : "400px" }} className="min-w-0 overflow-hidden rounded border border-slate-300 dark:border-slate-700" />
    </div>
  );
}
