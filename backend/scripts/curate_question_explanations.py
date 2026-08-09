"""Add only high-confidence, beginner-friendly question explanations.

The generated catalog is keyed by normalized content rather than database IDs,
so reviewed explanations survive reseeding and re-importing. Questions outside
the conservative rules are written to the human-review report, not guessed.

Usage:
    .venv/bin/python scripts/curate_question_explanations.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.quiz import Question, Quiz  # noqa: E402
from app.services.question_explanation_catalog import (  # noqa: E402
    CATALOG_PATH,
    question_signature,
)


EXPLANATIONS_BY_ANSWER = {
    "Bluetooth": "Bluetooth is a short-range wireless standard used to connect personal devices such as headsets, keyboards, and phones in a WPAN.",
    "S.M.A.R.T.": "S.M.A.R.T. records drive-health indicators and can warn about signs of an impending HDD or SSD failure.",
    "Trackpad": "A trackpad is the built-in touch-sensitive pointing surface commonly used on a laptop.",
    "5G": "5G is the current major generation of cellular networking, following 4G LTE and offering higher capacity and lower latency where supported.",
    "GPS": "GPS uses satellite signals to determine a device's location, which is what locator applications rely on.",
    "MDM": "Mobile device management (MDM) lets an organization centrally configure devices, deploy apps, and enforce security policies.",
    "Rootkit": "A rootkit hides malicious activity and helps an attacker keep privileged access, which makes it especially difficult to detect.",
    "Spyware": "Spyware secretly gathers information about a user or device without informed consent.",
    "Ransomware": "Ransomware blocks access to data or a system, commonly through encryption, and demands an action or payment for recovery.",
    "Vishing": "Vishing is phishing carried out through voice calls; smishing uses SMS and ordinary phishing commonly uses email or web messages.",
    "Smishing": "Smishing is phishing delivered by SMS or text message; vishing is the voice-call equivalent.",
    "Spear phishing": "Spear phishing targets a particular person or group with tailored details, unlike a broad untargeted phishing campaign.",
    "Whaling": "Whaling is a targeted phishing attack aimed at senior executives or other high-value decision makers.",
    "Shoulder surfing": "Shoulder surfing means observing someone's screen or keyboard to steal information; a privacy filter reduces the usable viewing angle.",
    "Tailgating": "Tailgating occurs when an unauthorized person follows an authorized person into a restricted area without presenting their own credentials.",
    "DDoS": "A distributed denial-of-service attack floods a target from many systems, whereas a basic DoS attack may come from one source.",
    "Zero-day attack": "A zero-day attack exploits a vulnerability before a vendor patch is available or defenders have had time to respond.",
    "Spoofing": "Spoofing falsifies an identifier, such as an email, IP, MAC address, or caller ID, so the source appears trusted.",
    "Safe Mode": "Safe Mode starts Windows with a minimal set of drivers and services, reducing the chance that persistent malware can interfere with removal tools.",
    "Device encryption": "Device encryption makes stored data unreadable without the correct authentication key, protecting it if the device is lost or stolen.",
    "PIN code": "A PIN is a knowledge factor: authentication depends on something the user knows rather than something they have or are.",
    "Pattern unlock": "Pattern unlock requires the user to trace a previously chosen path across points on an Android lock screen.",
    "Erasing/wiping": "Secure wiping overwrites or cryptographically erases recoverable data while leaving the storage device available for reuse.",
    "Low-level format": "A low-level format reinitializes a drive's physical sector layout; it is different from creating a normal file system with a standard format.",
    "Standard format": "A standard format creates new file-system structures but may leave old data recoverable until it is overwritten.",
    "Content filtering": "Content filtering examines traffic or requested content against rules and blocks material that matches prohibited patterns or categories.",
    "bootrec /fixboot": "`bootrec /fixboot` writes a new boot sector and is used when Windows boot configuration or boot-sector data is damaged.",
    "hosts": "The hosts file can override DNS name resolution locally, so malicious entries can redirect names to incorrect IP addresses.",
    "Full backup": "A full backup copies every selected item, making restores simple but using more time and storage than incremental methods.",
    "Incremental backup": "An incremental backup copies changes since the most recent backup of any type; restores need the last full backup plus each later incremental.",
    "Differential backup": "A differential backup copies changes since the last full backup; restoring needs the full backup and the latest differential.",
    "Synthetic full backup": "A synthetic full combines an earlier full backup with later backup data to create a new full set without rereading every source file.",
    "MSDS": "A material safety data sheet documents a chemical's hazards, safe handling, protective equipment, and emergency procedures.",
    "HVAC": "Heating, ventilation, and air conditioning (HVAC) controls temperature and airflow in equipment spaces.",
    "Thermal throttling": "Thermal throttling reduces component speed when temperature rises too far, preventing damage at the cost of performance.",
    "EULA": "An end-user license agreement defines the legal terms under which software may be installed and used.",
    "RDP": "Remote Desktop Protocol (RDP) provides graphical remote control of supported Windows systems and normally uses TCP port 3389.",
    "VPN": "A VPN creates an encrypted tunnel across an untrusted network so a remote device can securely reach private resources.",
    "VNC": "VNC provides cross-platform graphical remote control. Because basic VNC may lack strong transport encryption, it should be protected with a VPN or SSH tunnel.",
    "SSH": "SSH provides encrypted command-line administration and file transfer, making it the secure replacement for Telnet.",
    "RMM": "Remote monitoring and management (RMM) platforms let support teams centrally monitor, maintain, and assist many endpoints.",
    "SPICE": "SPICE is an open remote-display protocol designed for interacting with virtual machines.",
    "WinRM": "Windows Remote Management (WinRM) supports remote command and PowerShell execution without requiring a graphical desktop session.",
    "Port 3389": "RDP listens on TCP port 3389 by default, so that port needs tight firewall and access controls.",
    "HTTPS": "HTTPS carries HTTP over TLS, encrypting the traffic and authenticating the server certificate.",
    "Plagiarism": "Presenting another source's words or AI-generated work as your own without attribution is plagiarism; human review does not remove the need for attribution.",
    "Bias": "Bias is a systematic skew in an AI system's results, often caused by unrepresentative historical training data.",
    "HTTP": "HTTP is the application protocol browsers use to request web resources; HTTPS adds TLS protection.",
    "SMTP": "Simple Mail Transfer Protocol (SMTP) sends email between clients and mail servers or between mail servers.",
    "DHCP": "DHCP automatically supplies clients with IP configuration such as an address, subnet mask, gateway, and DNS servers.",
    "SMB": "Server Message Block (SMB) provides network file and printer sharing and is widely used in Windows environments.",
    "Mail server": "A mail server handles electronic messages with sending protocols such as SMTP and retrieval protocols such as IMAP.",
    "Syslog server": "A syslog server centralizes diagnostic and event messages from network devices and systems for monitoring and investigation.",
    "Web server": "A web server responds to HTTP or HTTPS requests and can deliver both static content and web application responses.",
    "Database management system": "SQL Server is a relational database management system used to store, query, secure, and manage structured data.",
    "NTP": "Network Time Protocol (NTP) synchronizes clocks across networked devices, which is important for logs and authentication.",
    "UTM": "Unified threat management combines several protections, such as firewalling, filtering, and intrusion prevention, in one security platform.",
    "Proxy server": "A proxy relays requests between clients and other networks and can filter, cache, or log those requests.",
    "IoT": "The Internet of Things (IoT) is a network of sensor-equipped physical devices that exchange data and perform connected tasks.",
    "A": "A DNS A record maps a hostname to a 32-bit IPv4 address; an AAAA record maps a hostname to IPv6.",
    "IPv6 address": "A DNS AAAA record maps a hostname to an IPv6 address; an A record is used for IPv4.",
    "CNAME": "A CNAME record makes one DNS name an alias of another canonical hostname.",
    "MX": "A DNS MX record identifies the mail servers that accept email for a domain.",
    "Access point": "A wireless access point bridges Wi-Fi clients onto a wired network; a router connects different IP networks.",
    "Patch panel": "A patch panel provides organized, passive termination points for building cabling; it does not switch or route traffic.",
    "Firewall": "A firewall permits or blocks incoming and outgoing traffic according to defined security rules.",
    "PoE injector": "A PoE injector adds electrical power to an Ethernet link when the network switch does not supply PoE itself.",
    "ONT": "An optical network terminal converts the provider's fiber signal into customer-facing network connections at the demarcation point.",
    "NIC": "A network interface card or controller (NIC) is the hardware that connects a computer to a network.",
    "MAC": "A MAC address is a 48-bit link-layer identifier assigned to a network interface; it is different from an IP address.",
    "Address exhaustion": "IPv6 was developed largely because the available pool of 32-bit IPv4 addresses was being exhausted.",
    "SAN": "A storage area network (SAN) is a dedicated network that provides systems with centralized block-level storage.",
    "WLAN": "A wireless LAN (WLAN) connects devices across a local area using radio rather than Ethernet cabling.",
    "Cable stripper": "A cable stripper removes insulation without cutting the conductor, preparing the wire for termination.",
    "Toner & probe kit": "A toner sends a traceable signal onto a cable and the probe detects it, helping identify one cable in a bundle.",
    "Punchdown tool": "A punchdown tool seats and trims conductors in insulation-displacement terminals on patch panels or blocks.",
    "Loopback plug": "A loopback plug returns transmitted signals to the same interface, allowing a technician to test whether the NIC port works.",
    "Network tap": "A network tap copies traffic for monitoring while allowing the original data flow to continue.",
    "LCD": "LCD is the most common general display technology in modern computers; OLED uses self-emitting pixels instead of an LCD backlight.",
    "Touch screen": "A touch screen displays output and also accepts touch as input, so it performs both functions.",
    "STP": "Shielded twisted-pair (STP) cable includes shielding to reduce electromagnetic interference; UTP does not.",
    "RS-232": "RS-232 is a serial communication standard commonly associated with DB-9 connectors on PCs and network equipment.",
    "DVI-A": "DVI-A carries analog video, while DVI-D carries digital video.",
    "DVI-D": "DVI-D carries digital video, while DVI-A carries analog video.",
    "SODIMM": "A SODIMM is the compact memory-module form factor normally used in laptops and small systems.",
    "DIMM": "A full-size DIMM is the standard memory-module form factor used in desktop computers and servers.",
    "Parity bit": "A parity bit provides simple error detection by making the number of set bits odd or even; it cannot correct the error.",
    "Revolutions per minute": "RPM measures how quickly an HDD's platters rotate; higher spindle speed can reduce mechanical access time.",
    "ATX": "ATX is the common full-size desktop motherboard form factor, larger than microATX and ITX.",
    "microATX": "microATX is a smaller ATX-compatible motherboard form factor with fewer expansion slots than full ATX.",
    "ITX": "ITX form factors are designed for compact systems and use less board space than ATX or microATX.",
    "PCI": "PCI is an older parallel expansion-bus standard; modern systems generally use serial PCI Express.",
    "SATA": "SATA is the common serial interface for internal HDDs, SSDs, and optical drives.",
    "x86": "x86 commonly refers to the 32-bit Intel-compatible processor architecture and its instruction set.",
    "x64": "x64 is the 64-bit extension of x86 and can address much more memory than a 32-bit x86 system.",
    "RISC": "Reduced instruction set computing (RISC) uses a streamlined instruction set designed for efficient execution.",
    "VT-x": "Intel VT-x provides processor hardware support for virtualization.",
    "AMD-V": "AMD-V provides AMD processor hardware support for virtualization.",
    "Watt": "A watt measures power: the rate at which electrical energy is used or delivered.",
    "Firmware": "Firmware is low-level software stored on hardware that controls how the device starts and operates.",
    "USB": "USB is a general peripheral interface that can carry data and power; it is not a network protocol.",
    "Ethernet": "Ethernet is the dominant wired LAN technology and is standardized by IEEE 802.3.",
    "Print server": "A print server shares printers and manages print jobs for multiple network users.",
    "Calibration": "Printer calibration aligns color output and print positioning so the result matches the intended image.",
    "Ink cartridge": "An ink cartridge supplies liquid ink to an inkjet printer; toner is used by laser printers.",
    "Printhead": "The printhead places ink onto paper through tiny nozzles; clogged nozzles can cause missing lines or colors.",
    "Impact": "An impact printer physically strikes an inked ribbon, which allows it to print multipart forms.",
    "Multipart": "Multipart forms work with impact printers because the print mechanism physically transfers pressure through several layers.",
    "Multitenancy": "Multitenancy lets multiple customers share cloud infrastructure while keeping each tenant's data and configuration logically isolated.",
    "SLA": "A service-level agreement (SLA) defines measurable commitments such as availability, response time, and support expectations.",
    "HDD drives": "Traditional HDDs benefit from defragmentation because files can become scattered across physical platters; SSDs should not be routinely defragmented.",
    "RAID 0": "RAID 0 stripes data for performance but provides no redundancy; one disk failure loses the whole array.",
    "IOPS": "Input/output operations per second (IOPS) measures how many storage operations a device can complete each second.",
    "DNS": "DNS translates hostnames into IP addresses. DHCP assigns IP configuration, so it is not the service for name resolution.",
    "Jitter": "Jitter is variation in packet delay; high jitter causes uneven delivery that is especially noticeable in voice and video.",
    "Imaging drum": "In a laser printer, the imaging drum carries the electrostatic image that attracts toner before transfer to paper.",
    "NTFS": "NTFS is the standard Windows file system and supports permissions, journaling, compression, and large volumes.",
    "ReFS": "ReFS is a Microsoft file system designed for data integrity and resilience, especially on large storage systems.",
    "FAT32": "FAT32 is broadly compatible but has a 4 GB maximum individual file size and lacks modern permissions.",
    "ext4": "ext4 is a widely used journaling file system for Linux.",
    "XFS": "XFS is a high-performance journaling file system commonly used on Linux for large files and volumes.",
    "exFAT": "exFAT supports large files and broad removable-drive compatibility without NTFS's Windows permission features.",
    "APFS": "Apple File System (APFS) is the modern default file system for macOS and Apple flash storage.",
    "Hot-swapping": "Hot-swapping means removing or installing supported hardware while the system remains powered on.",
    "Clean installation": "A clean installation replaces the prior operating-system installation rather than preserving its applications and settings.",
    "In-place upgrade": "An in-place upgrade installs a newer OS while preserving supported applications, settings, and user data.",
    "Image deployment": "Image deployment applies a prepared operating-system image so many computers receive a consistent configuration.",
    "PXE": "Preboot Execution Environment (PXE) lets a computer boot from network services for installation or imaging.",
    "BitLocker": "BitLocker provides full-volume encryption on supported Windows editions and protects data when a drive is offline.",
    "taskschd.msc": "`taskschd.msc` opens Task Scheduler, where automated tasks can be created and reviewed.",
    "devmgmt.msc": "`devmgmt.msc` opens Device Manager for reviewing hardware and managing device drivers.",
    "certmgr.msc": "`certmgr.msc` opens the current user's Windows certificate store.",
    "perfmon.exe": "Performance Monitor records and graphs detailed Windows performance counters over time.",
    "resmon.exe": "Resource Monitor shows real-time CPU, memory, disk, and network use by process.",
    "msconfig.exe": "System Configuration (`msconfig`) controls diagnostic startup options and related boot settings.",
    "cd": "The `cd` command changes the current working directory.",
    "dir": "The Windows `dir` command lists files and folders in a directory; Linux and macOS normally use `ls`.",
    "ipconfig": "`ipconfig` displays and manages IP configuration on Windows; Linux commonly uses `ip addr`.",
    "ping": "`ping` sends ICMP echo requests to test basic reachability and measure round-trip time.",
    "nslookup": "`nslookup` queries DNS so a technician can test name resolution separately from basic IP connectivity.",
    "net use": "The Windows `net use` command connects, lists, or disconnects shared network resources.",
    "tracert": "Windows `tracert` shows the network hops toward a destination; Linux and macOS commonly use `traceroute`.",
    "pathping": "`pathping` combines route tracing with packet-loss measurements for the hops along a Windows network path.",
    "Network discovery": "Windows network discovery lets a computer find other network devices and be found by them on an allowed network profile.",
    ".pkg": "A `.pkg` file is a standard macOS installer package.",
    "App Store": "The Mac App Store is Apple's managed source for discovering, installing, and updating approved macOS applications.",
    "/Applications": "macOS normally stores system-wide applications in `/Applications`.",
    "/etc/passwd": "`/etc/passwd` stores Unix account information; password hashes are normally protected in `/etc/shadow`.",
    "/etc/shadow": "`/etc/shadow` stores protected Linux password hashes and password-aging data.",
    "/etc/hosts": "`/etc/hosts` provides local static hostname-to-address mappings before or alongside DNS resolution.",
    "Principle of least privilege": "Least privilege gives each user or process only the access needed for its work, limiting damage from mistakes or compromise.",
    "Zero Trust model": "Zero Trust continually verifies identity, device, and context instead of assuming that an internal network location is trustworthy.",
    "ACL": "An access control list (ACL) states which identities are allowed or denied specific permissions on a resource.",
    "Hardware token": "A hardware token is a possession factor: it proves something the user physically has.",
    "OTP": "A one-time password is valid for only one authentication event or short period, reducing the value of a captured code.",
    "WPA3": "WPA3 is the current Wi-Fi security generation and improves protection compared with WPA2 and obsolete WEP.",
    "TKIP": "TKIP was a transitional WPA encryption method; modern networks should use AES-based CCMP rather than TKIP.",
}

UNSAFE_QUESTION_IDS = {
    647: "The keyed answer is Event Viewer, but Task Manager or Resource Monitor is normally used to identify resource-intensive applications.",
    651: "The keyed answer is Windows Update, but Device Manager is normally used to roll back a specific device driver.",
}


def _options(question: Question) -> list[str]:
    return [
        value or ""
        for value in (question.option_a, question.option_b, question.option_c, question.option_d,
                      question.option_e, question.option_f, question.option_g, question.option_h)
    ]


def _correct_text(question: Question) -> str:
    return getattr(question, f"option_{question.correct_answer.lower()}") or ""


def _true_statement_explanation(question: Question) -> str | None:
    if _correct_text(question).strip().casefold() != "true":
        return None
    statement = " ".join(question.question_text.split())
    if len(statement) > 420:
        sentences = re.split(r"(?<=[.!?])\s+", statement)
        statement = " ".join(sentences[:2])
    if len(statement) > 420:
        return None
    return f"This is true. {statement}"


def explanation_for(question: Question) -> str | None:
    if question.id in UNSAFE_QUESTION_IDS or question.is_multi_select:
        return None
    direct = EXPLANATIONS_BY_ANSWER.get(_correct_text(question).strip())
    return direct or _true_statement_explanation(question)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Update missing explanations in the configured database")
    parser.add_argument("--report", default="../docs/question_explanation_review.json")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        questions = db.query(Question).order_by(Question.id).all()
        catalog: dict[str, str] = {}
        added_ids: list[int] = []
        review: list[dict] = []
        for question in questions:
            if question.explanation and question.explanation.strip():
                continue
            explanation = explanation_for(question)
            options = _options(question)
            answers = question.all_correct_answers
            if explanation:
                catalog[question_signature(question.question_text, options, answers)] = explanation
                added_ids.append(question.id)
                if args.apply:
                    question.explanation = explanation
            else:
                quiz = db.get(Quiz, question.quiz_id)
                review.append({
                    "question_id": question.id,
                    "quiz_id": question.quiz_id,
                    "quiz_title": quiz.title if quiz else None,
                    "reason": UNSAFE_QUESTION_IDS.get(
                        question.id,
                        "No conservative high-confidence explanation rule matched; editorial review required.",
                    ),
                })

        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "explanations": dict(sorted(catalog.items())),
        }, indent=2) + "\n", encoding="utf-8")
        report_path = (BACKEND_ROOT / args.report).resolve()
        report_path.write_text(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "questions_before": len([q for q in questions if not q.explanation]) + (len(added_ids) if args.apply else 0),
            "explanations_added": len(added_ids),
            "added_question_ids": added_ids,
            "human_review_count": len(review),
            "human_review": review,
        }, indent=2) + "\n", encoding="utf-8")
        if args.apply:
            touched_quiz_ids = {question.quiz_id for question in questions if question.id in added_ids}
            for quiz_id in touched_quiz_ids:
                quiz = db.get(Quiz, quiz_id)
                if quiz:
                    quiz.explanations_complete = not db.query(Question.id).filter(
                        Question.quiz_id == quiz_id,
                        (Question.explanation.is_(None)) | (Question.explanation == ""),
                    ).first()
            db.commit()
        print(json.dumps({"added": len(added_ids), "human_review": len(review), "applied": args.apply}))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
