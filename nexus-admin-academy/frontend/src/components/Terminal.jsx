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
  } else if (command === "get-process") {
    term.writeln("Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id  ProcessName");
    term.writeln("-------  ------    -----      -----     ------     --  -----------");
    term.writeln("    156      12     2548      12456       0.50   1234  chrome");
    term.writeln("     89       8     1824       8932       2.30   5678  explorer");
  } else if (command === "cls" || command === "clear") {
    term.clear();
  } else if (!command || command === "help") {
    term.writeln("Available commands:");
    term.writeln("  ipconfig");
    term.writeln("  ping [host]");
    term.writeln("  Get-Service");
    term.writeln("  Get-Process");
    term.writeln("  cls/clear");
  } else {
    term.writeln(`'${cmd}' is not recognized as a command.`);
    term.writeln("Type help for available commands.");
  }
  term.writeln("");
}

export default function TerminalWidget() {
  const terminalRef = useRef(null);

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: "Consolas, monospace",
      theme: { background: "#1e1e1e", foreground: "#ffffff" },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    let currentLine = "";
    term.writeln("Windows PowerShell Practice Terminal");
    term.writeln("Type commands to practice (simulated environment)");
    term.writeln("Available: ipconfig, ping, Get-Service, Get-Process");
    term.writeln("");
    term.write("PS C:\\Users\\Student> ");

    term.onData((data) => {
      if (data === "\r") {
        term.write("\r\n");
        processCommand(currentLine, term);
        currentLine = "";
        term.write("PS C:\\Users\\Student> ");
      } else if (data === "\u007f") {
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          term.write("\b \b");
        }
      } else if (data === "\u0003") {
        term.write("^C\r\nPS C:\\Users\\Student> ");
        currentLine = "";
      } else {
        currentLine += data;
        term.write(data);
      }
    });

    const onResize = () => fitAddon.fit();
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      term.dispose();
    };
  }, []);

  return (
    <div className="rounded-lg border border-slate-300 bg-white p-4 shadow dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-200">Practice Terminal</div>
      <div ref={terminalRef} style={{ height: "400px" }} className="rounded border border-slate-300 dark:border-slate-700" />
    </div>
  );
}
