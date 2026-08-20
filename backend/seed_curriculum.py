"""Run once to seed the curriculum from the hardcoded data."""
import sys

sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.curriculum_video import CurriculumVideo
from app.services.training_curriculum_seed import (
    reconcile_week_zero_requirements,
    reconcile_optional_lesson_requirements,
    reconcile_video_requirements,
    sync_initial_training_activities,
    sync_weeks_1_4_practice_realignment,
    sync_weeks_3_6_quality,
    sync_weeks_7_10_quality,
    sync_weeks_11_14_quality,
    sync_weeks_15_18_quality,
    sync_weeks_19_22_quality,
)
from app.services.training_reference_seed import ensure_training_reference_content

CURRICULUM = [
    # (section, section_order, title, duration, url, quiz_title, video_order)
    ("Mobile Devices", 0, "Laptop Hardware", "16:42", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/laptop-hardware-220-1201/", "Mobile Device Hardware Servicing Quiz", 0),
    ("Mobile Devices", 0, "Connecting Mobile Devices", "6:08", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/connecting-mobile-devices-220-1201/", "Mobile Device Connection Methods Quiz", 1),
    ("Mobile Devices", 0, "Mobile Device Accessories", "7:18", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/mobile-device-accessories-220-1201/", "Mobile Device Accessories Quiz", 2),
    ("Mobile Devices", 0, "Mobile Device Networks", "10:14", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/mobile-device-networks-220-1201/", "Mobile Device Network Connectivity Quiz", 3),
    ("Mobile Devices", 0, "Mobile Device Management", "8:31", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/mobile-device-management-220-1201/", "Mobile Device Application Support Quiz", 4),
    ("Networking", 1, "Introduction to IP", "19:04", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/introduction-to-ip-220-1201/", "Network Protocols Quiz", 0),
    ("Networking", 1, "Common Ports", "12:52", "https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/common-ports-220-1201/", "TCP & UDP Ports Quiz", 1),
    ("Networking", 1, "Wireless Network Technologies", "7:16", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/wireless-network-technologies-220-1201/", "Wireless Networking Technologies Quiz", 2),
    ("Networking", 1, "Network Services", "17:03", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/network-services-220-1201/", "Network Services Quiz", 3),
    ("Networking", 1, "DNS Configuration", "18:18", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/dns-configuration-220-1201/", "Network Configuration Concepts Quiz", 4),
    ("Networking", 1, "DHCP", "10:46", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/dhcp-220-1201/", "Network Configuration Concepts Quiz", 5),
    ("Networking", 1, "VLANs and VPNs", "7:32", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/vlans-and-vpns-220-1201/", "Network Configuration Concepts Quiz", 6),
    ("Networking", 1, "Network Devices", "18:01", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/network-devices-220-1201/", "Common Networking Hardware Quiz", 7),
    ("Networking", 1, "IPv4 and IPv6", "8:45", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/ipv4-and-ipv6-220-1201/", "IP Addressing Quiz", 8),
    ("Networking", 1, "Assigning IP Addresses", "8:26", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/assigning-ip-addresses-220-1201/", "IP Addressing Quiz", 9),
    ("Networking", 1, "Internet Connection Types", "7:33", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/internet-connection-types-220-1201/", "Internet Connection Types Quiz", 10),
    ("Networking", 1, "Network Types", "4:46", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/network-types-220-1201/", "Network Types Quiz", 11),
    ("Networking", 1, "Network Tools", "11:48", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/network-tools-220-1201/", "Networking Tools Quiz", 12),
    ("Hardware", 2, "Display Types", "9:13", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/display-types-220-1201/", "Display Devices Quiz", 0),
    ("Hardware", 2, "Display Attributes", "12:01", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/display-attributes-220-1201/", "Display Devices Quiz", 1),
    ("Hardware", 2, "Network Cables", "12:14", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/network-cables-220-1201/", "Cabling Quiz", 2),
    ("Hardware", 2, "568A and 568B Colors", "5:41", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/568a-and-568b-colors-220-1201/", "Cabling Quiz", 3),
    ("Hardware", 2, "Optical Fiber", "4:14", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/optical-fiber-220-1201/", "Cabling Quiz", 4),
    ("Hardware", 2, "Peripheral Cables", "8:59", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/peripheral-cables-220-1201/", "Cabling Quiz", 5),
    ("Hardware", 2, "Video Cables", "7:03", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/video-cables-220-1201/", "Cabling Quiz", 6),
    ("Hardware", 2, "Storage Cables", "4:10", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/storage-cables-220-1201/", "Cabling Quiz", 7),
    ("Hardware", 2, "Adapters and Converters", "4:05", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/adapters-and-converters-220-1201/", "Connector Quiz", 8),
    ("Hardware", 2, "Copper Connectors", "8:33", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/copper-connectors-220-1201/", "Connector Quiz", 9),
    ("Hardware", 2, "Fiber Connectors", "2:49", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/fiber-connectors-220-1201/", "Connector Quiz", 10),
    ("Hardware", 2, "An Overview of Memory", "8:38", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/an-overview-of-memory-220-1201/", "RAM Quiz", 11),
    ("Hardware", 2, "Memory Technologies", "8:44", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/memory-technologies-220-1201/", "RAM Quiz", 12),
    ("Hardware", 2, "Storage Devices", "14:54", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/storage-devices-220-1201/", "Storage Devices Quiz", 13),
    ("Hardware", 2, "RAID", "8:08", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/raid-220-1201/", "Storage Devices Quiz", 14),
    ("Hardware", 2, "Motherboard Form Factors", "6:18", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/motherboard-form-factors-220-1201/", "Motherboard Quiz", 15),
    ("Hardware", 2, "Motherboard Expansion Slots", "7:14", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/motherboard-expansion-slots-220-1201/", "Motherboard Quiz", 16),
    ("Hardware", 2, "Motherboard Connections", "5:45", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/motherboard-connections-220-1201/", "Motherboard Quiz", 17),
    ("Hardware", 2, "Motherboard Compatibility", "3:29", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/motherboard-compatibility-220-1201/", "Motherboard Quiz", 18),
    ("Hardware", 2, "The BIOS", "4:42", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/the-bios-220-1201/", "BIOS Quiz", 19),
    ("Hardware", 2, "BIOS Settings", "19:29", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/bios-settings-220-1201/", "BIOS Quiz", 20),
    ("Hardware", 2, "HSM and TPM", "7:47", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/hsm-and-tpm-220-1201/", "BIOS Quiz", 21),
    ("Hardware", 2, "CPU Features", "5:13", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/cpu-features-220-1201/", "CPU Quiz", 22),
    ("Hardware", 2, "Expansion Cards", "6:17", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/expansion-cards-220-1201/", "Motherboard Quiz", 23),
    ("Hardware", 2, "Cooling", "6:37", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/cooling-220-1201/", "Core PC Hardware Troubleshooting Quiz", 24),
    ("Hardware", 2, "Computer Power", "15:31", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/computer-power-220-1201/", "Power Supply Quiz", 25),
    ("Hardware", 2, "Multifunction Devices", "14:25", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/multifunction-devices-220-1201/", "Multifunction Devices Quiz", 26),
    ("Hardware", 2, "Laser Printer Maintenance", "7:30", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/laser-printer-maintenance-220-1201/", "Printer Quiz", 27),
    ("Hardware", 2, "Inkjet Printers", "3:29", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/inkjet-printers-220-1201/", "Printer Quiz", 28),
    ("Hardware", 2, "Inkjet Printer Maintenance", "3:54", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/inkjet-printer-maintenance-220-1201/", "Printer Quiz", 29),
    ("Hardware", 2, "Thermal Printers", "3:39", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/thermal-printers-220-1201/", "Printer Quiz", 30),
    ("Hardware", 2, "Thermal Printer Maintenance", "4:16", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/thermal-printer-maintenance-220-1201/", "Printer Quiz", 31),
    ("Hardware", 2, "Impact Printers", "6:19", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/impact-printers-220-1201/", "Printer Quiz", 32),
    ("Hardware", 2, "Impact Printer Maintenance", "3:11", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/impact-printer-maintenance-220-1201/", "Printer Quiz", 33),
    ("Virtualization & Cloud", 3, "Virtualization Concepts", "5:45", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/virtualization-concepts-220-1201/", "Virtualization Concepts Quiz", 0),
    ("Virtualization & Cloud", 3, "Virtualization Services", "11:23", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/virtualization-services-220-1201/", "Virtualization Concepts Quiz", 1),
    ("Virtualization & Cloud", 3, "Cloud Models", "9:48", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/cloud-models-220-1201/", "Cloud Computing Concepts Quiz", 2),
    ("Virtualization & Cloud", 3, "Cloud Characteristics", "6:50", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/cloud-characteristics-220-1201/", "Cloud Computing Concepts Quiz", 3),
    ("Hardware & Network Troubleshooting", 4, "Troubleshooting Hardware", "25:15", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/troubleshooting-hardware-220-1201/", "Core PC Hardware Troubleshooting Quiz", 0),
    ("Hardware & Network Troubleshooting", 4, "Troubleshooting Storage Devices", "17:04", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/troubleshooting-storage-devices-220-1201/", "Storage and RAID Troubleshooting Quiz", 1),
    ("Hardware & Network Troubleshooting", 4, "Troubleshooting Display Issues", "18:52", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/troubleshooting-display-issues-220-1201/", "Display Devices Troubleshooting Quiz", 2),
    ("Hardware & Network Troubleshooting", 4, "Troubleshooting Mobile Devices", "17:52", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/troubleshooting-mobile-devices-220-1201/", "Mobile Devices Troubleshooting Quiz", 3),
    ("Hardware & Network Troubleshooting", 4, "Troubleshooting Networks", "15:14", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/troubleshooting-networks-220-1201/", "Network Troubleshooting Quiz", 4),
    ("Hardware & Network Troubleshooting", 4, "Troubleshooting Printers", "11:54", "https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/troubleshooting-printers-220-1201/", "Printer Troubleshooting Quiz", 5),
]

JOB_RELEVANCE = {
    "Mobile Device Hardware Servicing Quiz": "awareness",
    "Mobile Device Connection Methods Quiz": "awareness",
    "Mobile Device Accessories Quiz": "awareness",
    "Mobile Device Network Connectivity Quiz": "know_it",
    "Mobile Device Application Support Quiz": "know_it",
    "Network Protocols Quiz": "job_critical",
    "TCP & UDP Ports Quiz": "job_critical",
    "Wireless Networking Technologies Quiz": "job_critical",
    "Network Services Quiz": "job_critical",
    "Network Configuration Concepts Quiz": "job_critical",
    "Common Networking Hardware Quiz": "job_critical",
    "IP Addressing Quiz": "job_critical",
    "Internet Connection Types Quiz": "know_it",
    "Network Types Quiz": "know_it",
    "Networking Tools Quiz": "job_critical",
    "Display Devices Quiz": "know_it",
    "Cabling Quiz": "know_it",
    "Connector Quiz": "awareness",
    "RAM Quiz": "know_it",
    "Storage Devices Quiz": "know_it",
    "Motherboard Quiz": "awareness",
    "BIOS Quiz": "job_critical",
    "CPU Quiz": "awareness",
    "Power Supply Quiz": "awareness",
    "Multifunction Devices Quiz": "know_it",
    "Printer Quiz": "job_critical",
    "Virtualization Concepts Quiz": "job_critical",
    "Cloud Computing Concepts Quiz": "job_critical",
    "Core PC Hardware Troubleshooting Quiz": "job_critical",
    "Storage and RAID Troubleshooting Quiz": "know_it",
    "Display Devices Troubleshooting Quiz": "know_it",
    "Mobile Devices Troubleshooting Quiz": "awareness",
    "Network Troubleshooting Quiz": "job_critical",
    "Printer Troubleshooting Quiz": "job_critical",
}


def infer_job_relevance(video_title: str, quiz_title: str | None) -> str:
    if quiz_title and quiz_title in JOB_RELEVANCE:
        return JOB_RELEVANCE[quiz_title]

    title = (video_title or "").lower()
    if any(token in title for token in ["troubleshooting", "network", "ip", "dns", "dhcp", "cloud", "virtual"]):
        return "job_critical"
    if any(token in title for token in ["mobile", "motherboard", "power supply", "cpu", "connector"]):
        return "awareness"
    return "know_it"

db = SessionLocal()
try:
    for section, section_order, title, duration, url, quiz_title, video_order in CURRICULUM:
        job_relevance = infer_job_relevance(title, quiz_title)
        key = title.lower().replace(" ", "-").replace("&", "and").replace("/", "-")
        existing = db.query(CurriculumVideo).filter(CurriculumVideo.video_key == key).first()
        if not existing:
            db.add(
                CurriculumVideo(
                    video_key=key,
                    section=section,
                    section_order=section_order,
                    title=title,
                    duration=duration,
                    url=url,
                    quiz_title=quiz_title,
                    job_relevance=job_relevance,
                    video_order=video_order,
                )
            )
        else:
            existing.section = section
            existing.section_order = section_order
            existing.title = title
            existing.duration = duration
            existing.url = url
            existing.quiz_title = quiz_title
            existing.video_order = video_order
            existing.job_relevance = job_relevance
    db.commit()
    reference_result = ensure_training_reference_content(db)
    db.commit()
    training_result = sync_initial_training_activities(db)
    week_zero_result = reconcile_week_zero_requirements(db)
    optional_lesson_result = reconcile_optional_lesson_requirements(db)
    video_requirement_result = reconcile_video_requirements(db)
    practice_realignment_result = sync_weeks_1_4_practice_realignment(db)
    weeks_3_6_result = sync_weeks_3_6_quality(db)
    weeks_7_10_result = sync_weeks_7_10_quality(db)
    weeks_11_14_result = sync_weeks_11_14_quality(db)
    weeks_15_18_result = sync_weeks_15_18_quality(db)
    weeks_19_22_result = sync_weeks_19_22_quality(db)
    print(
        f"Curriculum seeded successfully; references: {reference_result}; "
        f"weekly activities: {training_result}; Week 0 requirements: {week_zero_result}; Optional lessons: {optional_lesson_result}; "
        f"Video requirements: {video_requirement_result}; "
        f"Weeks 1-4 practice: {practice_realignment_result}; Weeks 3-6 quality: {weeks_3_6_result}; "
        f"Weeks 7-10 quality: {weeks_7_10_result}; Weeks 11-14 quality: {weeks_11_14_result}; "
        f"Weeks 15-18 quality: {weeks_15_18_result}; Weeks 19-22 quality: {weeks_19_22_result}"
    )
finally:
    db.close()
