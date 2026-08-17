"""Reviewed video-to-quiz mappings for the guided My Training curriculum.

The 28 approved quizzes are intentionally shared across related videos.  These
records are evidence, not fuzzy title matching: each group was reviewed against
the quiz questions, lesson/module relationship, weekly goals, and video topic.
"""

from dataclasses import dataclass


EXACT = "exact"
TOPIC_GROUP = "topic_group"
WEEK_FALLBACK = "week_fallback"
CONFIDENCE_BY_BASIS = {
    EXACT: "Exact",
    TOPIC_GROUP: "Strong topical",
    WEEK_FALLBACK: "Week-level fallback",
}


@dataclass(frozen=True)
class VideoQuizMapping:
    quiz_id: int
    basis: str
    confidence: str
    evidence: str

    def metadata(self) -> dict:
        return {
            "quiz_id": self.quiz_id,
            "quiz_mapping_basis": self.basis,
            "quiz_mapping_confidence": self.confidence,
            "quiz_mapping_evidence": self.evidence,
        }


VIDEO_QUIZ_MAPPINGS: dict[int, VideoQuizMapping] = {}


def _map(video_ids, quiz_id, basis, confidence, evidence):
    for video_id in video_ids:
        if video_id in VIDEO_QUIZ_MAPPINGS:
            raise RuntimeError(f"Video {video_id} has more than one quiz mapping")
        VIDEO_QUIZ_MAPPINGS[video_id] = VideoQuizMapping(quiz_id, basis, confidence, evidence)


# Existing approved title-identical relationships.
_map([166, 168], 42, EXACT, "Exact", "Existing video.quiz_title exactly matches approved Ticketing Systems Quiz.")
_map([43, 57], 78, EXACT, "Exact", "Existing video.quiz_title exactly matches approved Core PC Hardware Troubleshooting Quiz.")
_map([174], 48, EXACT, "Exact", "Existing video.quiz_title exactly matches approved Incident Response Quiz.")

# Strong topic groups proven by question content and the related weekly lesson.
_map([176, 177], 1, TOPIC_GROUP, "Strong topical", "Professional communication is directly assessed by Ticket Writing Fundamentals.")
_map(range(30, 43), 78, TOPIC_GROUP, "Strong topical", "The hardware quiz assesses memory, storage, motherboard, BIOS, CPU, power, and thermal symptoms.")
_map([44], 78, TOPIC_GROUP, "Strong topical", "The hardware quiz directly assesses power delivery and PSU failure symptoms.")
_map([114, 115, 116], 3, TOPIC_GROUP, "Strong topical", "The Investigator's Toolkit assesses Task Manager, MMC/service, Event Viewer, and diagnostic-tool use.")
_map([117, 118], 4, TOPIC_GROUP, "Strong topical", "Windows Command-Line Diagnostics directly assesses the commands taught by these videos.")
_map([1], 78, TOPIC_GROUP, "Strong topical", "Laptop hardware is assessed by the approved broad hardware troubleshooting quiz.")
_map([2, 4], 9, TOPIC_GROUP, "Strong topical", "Mobile connectivity and mobile networking support the Client Network Triage objectives.")
_map([169, 175, 180], 5, TOPIC_GROUP, "Strong topical", "Change control, policy/authorization, escalation, and remote support are assessed by Help-Desk Operations.")
_map([58, 59, 60], 78, TOPIC_GROUP, "Strong topical", "Storage, display, and mobile-hardware symptoms are part of broad PC hardware troubleshooting.")
_map([162, 163], 6, TOPIC_GROUP, "Strong topical", "The Windows troubleshooting quiz assesses startup, application, and device/app fault isolation.")
_map([164, 165], 8, TOPIC_GROUP, "Strong topical", "Endpoint Security assesses malware, credential compromise, firewall, and safe response.")
_map([139], 7, TOPIC_GROUP, "Strong topical", "Windows security settings support the account, share, and effective-permission objectives.")
_map([133, 134, 137, 138, 143, 144, 156, 157, 158], 8, TOPIC_GROUP, "Strong topical", "The Endpoint Security quiz assesses malware, phishing, firewall, Defender, and safe response.")
_map([6, 7, 8, 16, 17, 18, 61, 121, 122, 123, 124], 9, TOPIC_GROUP, "Strong topical", "The Client Network Triage quiz assesses addressing, DNS, DHCP, tools, firewall, and network fault domains.")
_map([14, 15], 10, TOPIC_GROUP, "Strong topical", "IPv4 Addressing and Subnetting directly assesses the addressing concepts in these videos.")
_map([12, 13], 12, TOPIC_GROUP, "Strong topical", "Cisco CLI, VLANs, and Interfaces assesses VLAN and switching-device behavior.")
_map([9, 10, 11], 13, TOPIC_GROUP, "Strong topical", "Trunks, Routing, and Network Services directly assesses DHCP, DNS, routing, and network services.")
_map([141, 142, 160], 14, TOPIC_GROUP, "Strong topical", "Secure network administration assesses authentication, SSH, port security, and SOHO controls.")
_map([140], 15, TOPIC_GROUP, "Strong topical", "Active Directory Foundations directly assesses AD objects, groups, accounts, and access patterns.")
_map([135, 136], 15, TOPIC_GROUP, "Strong topical", "Authentication, authorization, and logical access are directly assessed by Active Directory Foundations.")
_map([178, 179], 18, TOPIC_GROUP, "Strong topical", "Server DNS/DHCP and PowerShell assesses scripting discovery, safe automation, and PowerShell use.")
_map([170], 19, TOPIC_GROUP, "Strong topical", "Server Operations, Backup, and Remoting directly assesses backup and restore practice.")
_map([128, 129, 130], 20, TOPIC_GROUP, "Strong topical", "Linux Fundamentals directly assesses Linux navigation, commands, permissions, and SSH.")
_map(list(range(145, 156)) + [161], 8, TOPIC_GROUP, "Strong topical", "The approved security quiz is the closest assessed security group for threats, phishing, credentials, malware, and browser controls.")
_map([159], 48, TOPIC_GROUP, "Strong topical", "Secure data destruction and evidence handling belong to the approved incident-response assessment group.")
_map([53, 54, 55, 56, 132], 23, TOPIC_GROUP, "Strong topical", "Cloud Concepts and Entra ID assesses cloud models, responsibility, identity, and cloud support.")

# Explicit reviewed fallbacks where the available approved quiz is broader than
# the individual video.  The action remains useful and never points to a quiz
# outside the reviewed curriculum without recording that lower confidence.
_map([182], 42, WEEK_FALLBACK, "Week-level fallback", "Week 0 has one approved orientation assessment; no exam-strategy quiz is approved.")
_map([167], 1, WEEK_FALLBACK, "Week-level fallback", "Asset records support Week 1 ticket documentation, but no narrower approved asset quiz exists.")
_map([19, 20], 78, WEEK_FALLBACK, "Week-level fallback", "The approved Week 2 hardware quiz is broader than display technology.")
_map([108, 109, 110, 111, 112, 113, 119, 120, 131], 3, WEEK_FALLBACK, "Week-level fallback", "The approved Windows toolkit quiz is the broadest Week 3 Windows assessment.")
_map([3, 5, 45, 46, 47, 48, 49, 50, 51, 52, 62, 181], 5, WEEK_FALLBACK, "Week-level fallback", "Help-Desk Operations is the approved Week 4 assessment; no approved peripheral-specific quiz exists.")
_map([125, 126, 127], 6, WEEK_FALLBACK, "Week-level fallback", "Windows Deep Troubleshooting is the approved Week 5 troubleshooting assessment; no approved macOS quiz exists.")
_map(range(21, 30), 12, WEEK_FALLBACK, "Week-level fallback", "The approved Week 10 networking quiz is broader than individual cable and connector videos.")
_map([171, 172, 173], 25, WEEK_FALLBACK, "Week-level fallback", "Integrated Operations Readiness is the only approved Week 24 assessment; no approved safety quiz exists.")


# Beginner workload overrides.  Content remains assigned and reviewable; these
# sets only decide which videos gate the next week.
BEGINNER_REQUIRED_VIDEO_IDS = {
    # Week 0 has exactly two gates: its orientation lesson and checkpoint quiz.
    # Videos remain assigned as optional extra practice.
    0: set(),
    3: {110, 114, 117, 118},
    4: {46, 47, 62, 169, 180},
    7: {137, 138, 143, 156, 157},
    8: {6, 7, 18, 61, 123},
    # Week 20's required path is Linux operations. These security videos are
    # useful review but duplicate Week 7 and stay available as optional work.
    20: set(),
}

# The Week 3 Defender/update lesson is repeated more coherently in Week 7.
OPTIONAL_LESSON_IDS = {10}
OPTIONAL_LESSON_TITLES = {"Anatomy of a Good Ticket", "Meet the Command Line"}


def mapping_metadata(video_id: int) -> dict:
    mapping = VIDEO_QUIZ_MAPPINGS.get(int(video_id))
    return mapping.metadata() if mapping else {}


def video_is_required(week_number: int, video_id: int, job_relevance: str) -> bool:
    override = BEGINNER_REQUIRED_VIDEO_IDS.get(int(week_number))
    if override is not None:
        return int(video_id) in override
    return job_relevance == "job_critical"
