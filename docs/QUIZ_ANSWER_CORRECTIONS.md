# Quiz Answer Corrections

Applied 2026-07-19 UTC by `backend/scripts/apply_quiz_answer_corrections.py`. The script is dry-run by default, requires `--confirm`, uses one transaction, and preserves all IDs. Exactly 120 confirmed malformed answer keys were corrected without guessing from answer position.

## Machine-readable correction record

The executable `CORRECT_ANSWERS` mapping in `backend/scripts/apply_quiz_answer_corrections.py` is the canonical machine-readable manifest. Each run prints quiz/question ID, stored old answer set, validated new answer set, reason, and validation URL.

| Question | Quiz | Old key | New key | Validation reason | Validation source |
|---:|---:|---|---|---|---|
| q569 | 26 | B,C,D | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q570 | 26 | B,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q573 | 26 | A,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q584 | 28 | A,B,C,D,E,F | B,C,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q585 | 28 | A,B,C,D,E,F | A,C,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q587 | 28 | C,D | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q599 | 30 | A,B | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q600 | 30 | A,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q649 | 39 | B,E | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://support.apple.com/guide/deployment/intro-to-device-management-dep1d89f0bff/web |
| q661 | 42 | A,C,D,E | A,C,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q662 | 42 | B,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q664 | 42 | B,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q666 | 43 | A,C,D | A,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q668 | 43 | B,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q669 | 43 | B,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q671 | 43 | A,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q672 | 43 | C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q673 | 43 | A,C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q674 | 43 | A,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks |
| q706 | 50 | A,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.hhs.gov/hipaa/for-professionals/privacy/laws-regulations/index.html |
| q707 | 50 | B,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.hhs.gov/hipaa/for-professionals/privacy/laws-regulations/index.html |
| q748 | 55 | B,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q749 | 55 | A,B | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q753 | 55 | A,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q756 | 55 | B,C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q758 | 55 | A,C,D | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q759 | 55 | A,B | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q760 | 55 | B,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q761 | 55 | C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q764 | 55 | B,C | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q765 | 55 | A,B | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q766 | 55 | A,B | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q767 | 56 | B,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q768 | 56 | A,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q769 | 56 | A,C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q770 | 56 | A,B,C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q772 | 56 | A,B,C,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q773 | 56 | B,C | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q774 | 56 | B,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q775 | 56 | A,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q776 | 56 | A,C | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q777 | 56 | A,B,C,D,E | C,D,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q778 | 56 | B,C | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q779 | 56 | B,C,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q781 | 56 | B,C | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q785 | 58 | A,B,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q787 | 58 | A,B,C | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q788 | 58 | A,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q792 | 58 | B,C,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q793 | 58 | A,B,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q794 | 58 | A,C,D | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q795 | 58 | A,C | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q796 | 58 | B,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q799 | 58 | B,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q801 | 58 | B,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml |
| q824 | 61 | A,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q825 | 61 | C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q826 | 61 | A,B,C,D,E,F | A,C,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q827 | 61 | A,C,E | A,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q828 | 61 | A,C,E | C,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q829 | 61 | A,C,E | D,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q830 | 61 | A,B,C,D,E,F | A,C,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q831 | 61 | A,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q832 | 61 | A,B | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q835 | 61 | A,B,C,D,E,F | A,D,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q836 | 61 | A,B,C,D,E,F | D,E,F | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q839 | 62 | A,B,D,F | A,D,F | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q846 | 62 | B,E | E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q847 | 63 | A,B,C,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q848 | 63 | A,B,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q850 | 63 | B,C | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q851 | 63 | A,B,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q859 | 64 | A,B | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.rfc-editor.org/rfc/rfc1918 |
| q863 | 65 | A,B,C,D,E,F | A,C,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q864 | 65 | A,B,C,D,E,F | A,B,C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q865 | 65 | A,B,C,E,F | A,C,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q871 | 65 | A,C,E,F | A,C,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q908 | 67 | A,B,D,E,F | B,E,F | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q909 | 67 | B,C,D,E,F | D,F | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q911 | 67 | A,B,C,D,E,F | A,C,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q912 | 67 | A,B,C,D,E | A,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q913 | 67 | A,B,C,D,E,F | D,E,F | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q968 | 71 | A,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q982 | 73 | A,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q983 | 73 | A,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q986 | 73 | A,B,E | A,B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q987 | 73 | A,B,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q988 | 73 | A,B,C,D,F | B,C,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q1031 | 77 | B,C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://csrc.nist.gov/publications/detail/sp/800-145/final |
| q1034 | 77 | C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://csrc.nist.gov/publications/detail/sp/800-145/final |
| q1035 | 77 | B,C,D,E | B,C,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://csrc.nist.gov/publications/detail/sp/800-145/final |
| q1036 | 77 | A,C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://csrc.nist.gov/publications/detail/sp/800-145/final |
| q1037 | 77 | A,B,C | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://csrc.nist.gov/publications/detail/sp/800-145/final |
| q1038 | 77 | B,C,D | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://csrc.nist.gov/publications/detail/sp/800-145/final |
| q1039 | 77 | A,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://csrc.nist.gov/publications/detail/sp/800-145/final |
| q1043 | 77 | A,B,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://csrc.nist.gov/publications/detail/sp/800-145/final |
| q1075 | 79 | A,B,C,D,E | A,B,C,D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q1085 | 79 | C,D | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q1087 | 79 | B,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.comptia.org/content/guides/a-guide-to-comptia-a-core-1-and-core-2 |
| q1114 | 81 | A,B | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.epa.gov/recycle/used-lithium-ion-batteries |
| q1115 | 81 | A,B | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.epa.gov/recycle/used-lithium-ion-batteries |
| q1118 | 81 | A,B | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.epa.gov/recycle/used-lithium-ion-batteries |
| q1131 | 81 | A,B | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.epa.gov/recycle/used-lithium-ion-batteries |
| q1137 | 81 | B,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://www.epa.gov/recycle/used-lithium-ion-batteries |
| q1177 | 84 | A,B,C,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1178 | 84 | A,B,C,D | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1179 | 84 | B,D | B | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1180 | 84 | A,B,C,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1181 | 84 | A,B,C,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1182 | 84 | C,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1184 | 84 | A,B,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1185 | 84 | A,B,C,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1230 | 89 | A,B,C,E,F | C,E,F | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1231 | 89 | A,B,C,D,E,F | B,C,E | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1244 | 91 | A,D | D | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1251 | 92 | A,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1254 | 92 | A,C,D | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1256 | 92 | A,B | A | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1257 | 92 | B,C | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |
| q1258 | 92 | A,C,D | C | Removed mutually exclusive, extra, count-mismatched, or empty-option keys after content review. | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands |

## Unsafe battery correction

q1114 now states: **If a mobile-device battery is swollen, stop using the device. Disconnect external power when it is safe to do so, never puncture or compress the battery, keep the device away from flammable materials without unsafe handling, and follow manufacturer, qualified battery-disposal, or emergency procedures.**

Explanation: True. Swelling indicates battery failure and possible fire risk: stop use, disconnect power if safe, do not puncture or compress it, isolate it from flammables, and use qualified disposal or emergency guidance.

## Validation scope after correction

- Quizzes 42, 48, and 78 were reviewed in full because they fill the approved Week 0, Week 23, and Week 2 required-assessment gaps. Their answer keys are marked validated and every question has an explanation.
- Other affected imported quizzes remain `needs_edit` with `answer_keys_validated=false`; correcting a confirmed malformed key does not assert that every other key in that quiz was reviewed.
- All 196 questions in required/gate/cumulative quizzes now have explanations. Across the whole corpus, 333 questions have explanations and 634 optional imported questions still need editorial explanation work.
- Seed single-answer positions were deterministically rebalanced after tests proved that the correct answer text and grading key remain paired and repeated seed runs are stable. Multi-select options were not shuffled. Required seed single-answer distribution is now A 32, B 41, C 37, D 42 rather than 81.5% B.
