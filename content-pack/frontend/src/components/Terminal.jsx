import { useEffect, useRef } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";

function processCommand(cmd, term) {
  const command = cmd.trim().toLowerCase();

  if (command === "ipconfig") {
    term.writeln("Windows IP Configuration");
    term.writeln("");
    term.writeln("Ethernet adapter Ethernet:");
    term.writeln("   IPv4 Address. . . . . . . . . . . : 192.168.1.100");
    term.writeln("   Subnet Mask . . . . . . . . . . . : 255.255.255.0");
    term.writeln("   Default Gateway . . . . . . . . . : 192.168.1.1");
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
    term.writeln("C:\\Users\\Student");
  } else if (command.startsWith("cd ")) {
    const dir = command.split(" ")[1] || "~";
    term.writeln(`Changed directory to ${dir}`);
  } else if (command === "whoami") {
    term.writeln("NEXUS\\student01");
  } else if (command === "id") {
    term.writeln("uid=1001(student01) gid=1001(student01) groups=1001(student01),27(sudo)");
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
  } else if (command === "ps" || command.startsWith("ps ")) {
    term.writeln("  PID TTY          TIME CMD");
    term.writeln(" 1234 pts/0    00:00:00 bash");
    term.writeln(" 5678 pts/0    00:00:01 python3");
    term.writeln(" 9012 pts/0    00:00:00 ps");
  } else if (command.startsWith("systemctl status")) {
    const svc = command.split(" ")[2] || "nginx";
    term.writeln(`● ${svc}.service - ${svc} service`);
    term.writeln("   Loaded: loaded (/lib/systemd/system/nginx.service; enabled)");
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
    term.writeln("  ipconfig, ping [host], get-service, get-process, netstat, nslookup, arp");
    term.writeln("  ls, pwd, cd, whoami, id, uptime, free, df, ps, find, grep, cat");
    term.writeln("  tasklist, sc query <service>, netsh, dmesg, journalctl, ssh, curl, wget");
    term.writeln("  systemctl status/start/stop/restart <service>, chmod, chown, mkdir, kill");
    term.writeln("  cls/clear");
  } else {
    term.writeln(`'${cmd}' is not recognized as a command.`);
    term.writeln("Type help for available commands.");
  }
  term.writeln("");
}

export default function TerminalWidget({ prefillCommand, onSessionChange }) {
  const terminalRef = useRef(null);
  const termRef = useRef(null);
  const currentLineRef = useRef("");
  const historyRef = useRef([]);
  const historyIndexRef = useRef(-1);
  const sessionLinesRef = useRef([]);

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
    setTimeout(() => {
      try {
        fitAddon.fit();
      } catch {
        // no-op
      }
    }, 0);

    termRef.current = term;

    const prompt = "PS C:\\Users\\Student> ";

    const writePrompt = () => term.write(prompt);

    term.writeln("Windows PowerShell Practice Terminal");
    term.writeln("Type commands to practice (simulated environment)");
    term.writeln("Type help for command list");
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
        processCommand(command, term);
        sessionLinesRef.current.push("");
        currentLineRef.current = "";
        writePrompt();
        onSessionChange?.(sessionLinesRef.current.join("\n"));
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
      termRef.current = null;
      term.dispose();
    };
  }, [onSessionChange]);

  useEffect(() => {
    if (!prefillCommand || !termRef.current) return;
    const term = termRef.current;
    clearCurrentLine(term);
    currentLineRef.current = prefillCommand;
    term.write(prefillCommand);
  }, [prefillCommand]);

  return (
    <div className="rounded-lg border border-slate-300 bg-white p-4 shadow dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Practice Terminal</div>
      <div ref={terminalRef} style={{ height: "400px" }} className="rounded border border-slate-300 dark:border-slate-700" />
    </div>
  );
}
