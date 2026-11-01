#!/usr/bin/env python3
"""Build the demo mail corpus. Dev tool; outputs are committed.

    python3 demo/build/mail/make_mail.py            write everything
    python3 demo/build/mail/make_mail.py --check    rebuild in memory, compare with the files
                                                    on disk, exit 1 on any difference

Writes:
  demo/build/mail/out/*                    every attachment, as embedded (for review)
  demo/batches/1/, 2/, 3/*.eml             28 emails (b3-05 is a .msg written by demo/build/msg)
  demo/expected.csv                        29 rows, the answer key for check-filing
  demo/knowledge/standard-answers/*.docx   Kestrel's past security questionnaire (Sept 2025)
  tools/fixtures/sample.eml, sample.docx, EXPECTED.txt

Deterministic: fixed dates, fixed MIME boundaries, fixed zip entry times, reportlab invariant
mode. Needs Python 3.9+, python-docx 1.2, reportlab and Pillow.

Everything is invented: Kestrel Engineering Ltd, Kestrel Pumpen GmbH, every counterparty and
person. Times are local with the right offset around the clock change on 25 October 2026
(UK BST +0100 then GMT; Germany CEST +0200 then CET +0100).
"""

import argparse
import csv
import hashlib
import io
import shutil
import sys
from email import policy as email_policy
from email.parser import BytesParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import images  # noqa: E402
import legal_docs  # noqa: E402
import pdfs  # noqa: E402
from mailkit import DE, UK, Mail, local, message_id, outlook_file_name  # noqa: E402

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF = "application/pdf"

# ======================================================================= questionnaires
#
# Acme's 2026 questionnaire (attached to b2-02) has 40 questions. Kestrel's past questionnaire
# (demo/knowledge/standard-answers/, September 2025, owner IT Security) has 40 answered
# questions, worded and ordered differently. Its answers cover 38 of the 40 Acme questions.
#
# MAPPING (Acme question -> past questionnaire question). A checker can verify it against the
# two .docx tables; QUESTIONNAIRE_MAP below holds the same mapping and is asserted on build.
#   A01 -> P01  information security policy, approval, annual review
#   A02 -> P02  person responsible for information security
#   A03 -> P04  ISO/IEC 27001 certification (body, scope, expiry)
#   A04 -> P03  risk assessment, frequency, last one
#   A05 -> P08  security awareness training
#   A06 -> P06  pre-employment screening
#   A07 -> P07  confidentiality obligations in contracts
#   A08 -> P11  asset inventory with owners
#   A09 -> P09  information classification
#   A10 -> P10  where data is stored and processed
#   A11 -> P12  return, deletion, media disposal
#   A12 -> P14  least privilege, approval of access
#   A13 -> P15  multi-factor authentication
#   A14 -> P18  access reviews
#   A15 -> P19  leavers
#   A16 -> P17  privileged accounts
#   A17 -> P16  password policy
#   A18 -> P20  encryption in transit
#   A19 -> P21  encryption at rest, including backups
#   A20 -> P22  key management
#   A21 -> P23  anti-malware / EDR and alert handling
#   A22 -> P24  patch management timescales
#   A23 -> P25  vulnerability scanning (not penetration testing)
#   A24 -> P26  central logging, monitoring, retention
#   A25 -> P29  change management
#   A26 -> P38  backups, off-site, restore tests
#   A27 -> P30  separation of environments, live data in test
#   A28 -> P27  firewalls, segmentation, OT separation
#   A29 -> P31  how remote monitoring connects to customer networks
#   A30 -> P32  hardening and updating of gateways at customer sites
#   A31 -> P33  supplier security assessment
#   A32 -> P34  subcontractors and cloud providers
#   A33 -> P35  incident response plan and testing
#   A34 -> P36  incident notification time
#   A35 -> P37  incidents in the last three years
#   A36 -> P39  business continuity and disaster recovery
#   A37 -> P13  GDPR compliance and data protection lead
#   A38 -> P40  cyber insurance limit
#   A39 -> none SOC 2 Type II report: not covered (needs IT Security)
#   A40 -> none penetration test in the last 12 months: not covered (needs IT Security)
#   (past P05 Cyber Essentials Plus and P28 removable media are not asked by Acme)

QUESTIONNAIRE_MAP = {
    1: 1, 2: 2, 3: 4, 4: 3, 5: 8, 6: 6, 7: 7, 8: 11, 9: 9, 10: 10, 11: 12, 12: 14, 13: 15,
    14: 18, 15: 19, 16: 17, 17: 16, 18: 20, 19: 21, 20: 22, 21: 23, 22: 24, 23: 25, 24: 26,
    25: 29, 26: 38, 27: 30, 28: 27, 29: 31, 30: 32, 31: 33, 32: 34, 33: 35, 34: 36, 35: 37,
    36: 39, 37: 13, 38: 40, 39: None, 40: None,
}

ACME_QUESTIONS = [
    "Does your organisation have a documented information security policy that is approved by "
    "management and reviewed at least annually? Please state the date of the last review.",
    "Who in your organisation has overall responsibility for information security? Please give "
    "the role and reporting line.",
    "Is your information security management system certified to ISO/IEC 27001? If so, please "
    "give the certification body, the scope and the expiry date of the certificate.",
    "How often do you carry out a formal information security risk assessment, and when was the "
    "last one completed?",
    "Do all employees and contractors receive information security awareness training on "
    "joining and at least once a year?",
    "Are employees and contractors screened before they are given access to customer data or "
    "systems? Please describe the checks.",
    "Do employment contracts and contractor agreements include confidentiality obligations that "
    "continue after the engagement ends?",
    "Do you maintain an up-to-date inventory of information assets, including hardware, software "
    "and data, with a named owner for each?",
    "Do you classify information by sensitivity and apply handling rules to each class?",
    "In which countries and data centres will Acme data be stored and processed?",
    "How will Acme data be returned or securely deleted at the end of the contract, and how are "
    "storage media disposed of?",
    "Is access to systems and data granted on a least-privilege basis and approved by an "
    "authorised person?",
    "Is multi-factor authentication enforced for all remote access and for all privileged "
    "accounts?",
    "How often are user access rights reviewed, and by whom?",
    "How quickly are leavers' accounts disabled? Please state your target time.",
    "How are privileged (administrator) accounts controlled and monitored?",
    "What is your password policy (minimum length, complexity, lockout)?",
    "Is Acme data encrypted in transit? Please state the protocols and minimum versions.",
    "Is Acme data encrypted at rest, including in backups? Please state the algorithm.",
    "How are encryption keys generated, stored, rotated and protected?",
    "Is anti-malware or endpoint detection and response software installed on all servers and "
    "end-user devices, and how are alerts handled?",
    "Describe your patch management process, including target timescales for critical security "
    "patches.",
    "Do you carry out vulnerability scanning of internal and internet-facing systems? How often?",
    "Are security events logged centrally and monitored? How long are logs kept?",
    "Do you have a formal change management process for production systems?",
    "How often are backups taken? Are they encrypted and held off-site, and how often are "
    "restores tested?",
    "Are development, test and production environments separated, and is live data kept out of "
    "test?",
    "Are your networks protected by firewalls and segmented, including separation of operational "
    "technology from office IT?",
    "How will your personnel or systems connect to Acme networks (for example for remote "
    "condition monitoring), and how is that connection secured?",
    "How are your monitoring gateways or other devices installed at Acme sites hardened and kept "
    "up to date?",
    "How do you assess the information security of your own suppliers and subcontractors who may "
    "access Acme data?",
    "Please list all subcontractors and cloud providers that will store or process Acme data, "
    "with their role.",
    "Do you have a documented security incident response plan, and how often is it tested?",
    "Within what time will you notify Acme of a security incident affecting Acme data or "
    "systems?",
    "Have you had a security incident involving customer data in the last 36 months? If so, "
    "please describe it and the actions taken.",
    "Do you have business continuity and disaster recovery plans covering the services to Acme? "
    "Please state recovery time objectives and how often the plans are tested.",
    "How do you comply with the GDPR? Have you appointed a data protection officer, or who is "
    "responsible for data protection?",
    "Do you hold cyber insurance? Please state the limit of indemnity.",
    "Can you provide a current SOC 2 Type II report, or an equivalent independent assurance "
    "report, covering the services to Acme?",
    "Has an independent penetration test of your internet-facing systems and the monitoring "
    "platform been carried out in the last 12 months? Please give the date, the tester and the "
    "status of the findings.",
]

PAST_QUESTIONNAIRE = [
    ("Information security policy: do you have one, who approves it, and how often is it "
     "reviewed?",
     "Yes. Kestrel's Information Security Policy is approved by the Board and reviewed at least "
     "once a year by the Head of IT Security. The current version took effect on 1 January 2025; "
     "the next review is due in December 2025.",
     "Information Security Policy (2025)"),
    ("Who is accountable for information security?",
     "The Head of IT Security, who reports to the Chief Financial Officer and presents a security "
     "report to the Board every quarter.",
     "Information Security Policy, roles section"),
    ("Describe your information security risk assessment process.",
     "IT Security keeps the risk register for the information security management system. A full "
     "risk assessment is carried out every year and whenever there is a significant change; the "
     "last full assessment was completed in June 2025. Risks are reviewed monthly by the IT "
     "leadership team.",
     "Risk register; risk assessment report June 2025"),
    ("Which information security certifications do you hold? Please give certificate details.",
     "ISO/IEC 27001:2022. Scope: design, manufacture and remote condition monitoring of "
     "industrial pumps at the Sheffield site, including corporate IT and the monitoring platform. "
     "Certificate KE-ISMS-0417, issued by Halberd Certification Ltd, valid until 14 March 2027, "
     "with annual surveillance audits.",
     "ISO/IEC 27001 certificate; Statement of Applicability"),
    ("Do you hold Cyber Essentials or Cyber Essentials Plus certification?",
     "Yes, Cyber Essentials Plus, renewed every year. The current certificate runs until July "
     "2026.",
     "Cyber Essentials Plus certificate"),
    ("What pre-employment checks do you carry out?",
     "For all staff: identity, right to work, three years' employment history and two references. "
     "Staff with privileged IT access or access to customer systems also have a basic criminal "
     "record check.",
     "Recruitment and Screening Procedure"),
    ("Do staff and contractors sign confidentiality undertakings?",
     "Yes. Employment contracts and contractor agreements contain confidentiality clauses that "
     "continue after the engagement ends. Visitors to secure areas sign a confidentiality "
     "undertaking.",
     "Standard employment contract; contractor terms"),
    ("What security awareness training do staff receive?",
     "All staff and contractors complete online security awareness training at induction and an "
     "annual refresher, with quarterly simulated phishing exercises. Completion for 2024-25 was "
     "97%.",
     "Training records; phishing simulation reports"),
    ("How do you classify information?",
     "Four levels: Public, Internal, Confidential and Restricted. Customer data is Confidential as "
     "a minimum. Handling rules for each level (storage, sharing, encryption, disposal) are set "
     "out in the Information Classification Standard.",
     "Information Classification Standard"),
    ("Where is customer data hosted?",
     "In two UK data centres (primary and secondary) run for Kestrel by a colocation provider, and "
     "in Kestrel's cloud tenancy in UK regions. Customer data is not stored or processed outside "
     "the UK and the EEA.",
     "Data flow register; hosting contracts"),
    ("Do you keep an asset register?",
     "Yes. Hardware and software are recorded in a configuration management database that the "
     "endpoint management tool updates automatically. Information assets are recorded in the "
     "information asset register, each with a named owner.",
     "CMDB; information asset register"),
    ("How do you dispose of customer data and storage media?",
     "Customer data is returned or deleted within 30 days of the end of the contract unless the "
     "contract says otherwise, and deletion is confirmed in writing on request. Storage media are "
     "wiped to NIST SP 800-88 or physically destroyed by a certified disposal contractor, who "
     "issues certificates of destruction.",
     "Data Retention and Disposal Procedure"),
    ("How do you comply with data protection law?",
     "Kestrel Engineering Ltd complies with the UK GDPR and the Data Protection Act 2018, and "
     "Kestrel Pumpen GmbH with the EU GDPR. Kestrel is not required to appoint a data protection "
     "officer. The Legal team is responsible for data protection, supported by the Head of IT "
     "Security. Records of processing and a breach log are kept.",
     "Data Protection Policy; records of processing"),
    ("How is access to systems controlled?",
     "Role-based access on a least-privilege basis. Access requests are raised through the IT "
     "service desk and approved by the line manager and the system owner before they are "
     "granted.",
     "Access Control Policy"),
    ("Do you use multi-factor authentication?",
     "Yes. MFA is enforced for all remote access, email and cloud services, and for all "
     "administrator accounts.",
     "Access Control Policy; MFA configuration report"),
    ("What are your password requirements?",
     "At least 14 characters, checked against a list of known breached passwords; no forced "
     "periodic changes unless compromise is suspected; accounts lock after 10 failed attempts. "
     "This follows NCSC password guidance.",
     "Password Standard"),
    ("How are administrator accounts controlled?",
     "Administrators use separate named admin accounts, never shared, protected by MFA. Admin "
     "rights are granted just in time through a privileged access management tool, and privileged "
     "sessions are logged and reviewed.",
     "Privileged Access Procedure"),
    ("How often do you review access rights?",
     "Quarterly for critical systems and every six months for other systems, by the system "
     "owners. Privileged access is reviewed monthly by IT Security.",
     "Access review records"),
    ("How quickly is access removed when staff leave?",
     "Accounts are disabled at the end of the leaver's last working day, and within 4 hours for "
     "dismissals. The leaver process starts automatically from the HR system.",
     "Joiners, Movers and Leavers Procedure"),
    ("How is data protected in transit?",
     "TLS 1.2 or higher for all external connections, with TLS 1.3 preferred; SFTP for file "
     "transfers; site-to-site VPNs use IPsec with AES-256.",
     "Cryptography Standard"),
    ("Is data encrypted at rest?",
     "Yes. Servers and databases use AES-256 encryption, laptops have full-disk encryption, and "
     "backups are encrypted with AES-256.",
     "Cryptography Standard"),
    ("How are cryptographic keys managed?",
     "Keys are generated and held in a managed key vault backed by hardware security modules, "
     "rotated at least once a year, and access is limited to two named administrators.",
     "Cryptography Standard; key management procedure"),
    ("What protection against malware do you have?",
     "Endpoint detection and response on all servers and end-user devices, centrally managed. "
     "Alerts are monitored 24/7 by a managed security service provider, which escalates to IT "
     "Security.",
     "EDR deployment report; MSSP contract"),
    ("How do you apply security patches?",
     "Monthly patch cycle. Critical patches are applied within 14 days, or within 48 hours where a "
     "vulnerability is being actively exploited. Patch compliance is reported monthly to the Head "
     "of IT Security.",
     "Patch Management Procedure; monthly compliance report"),
    ("Do you scan for vulnerabilities?",
     "Yes. Authenticated internal vulnerability scans run monthly and external scans of "
     "internet-facing systems run weekly. Findings are tracked to closure within the patching "
     "timescales.",
     "Vulnerability scan reports"),
    ("Describe your security logging and monitoring.",
     "Logs from servers, firewalls, cloud services and endpoints feed a central SIEM that the "
     "managed security service provider monitors 24/7. Logs are kept for 12 months.",
     "Logging and Monitoring Standard"),
    ("How is your network protected?",
     "Next-generation firewalls at the perimeter and between network zones. The network is "
     "segmented into office, server, factory (operational technology) and guest zones, and the "
     "factory OT network is isolated from the office network.",
     "Network diagram; firewall rule reviews"),
    ("How do you control the use of removable media?",
     "USB storage devices are blocked by default on all end-user devices. Exceptions need IT "
     "Security approval and use encrypted company-issued devices.",
     "Removable Media Standard"),
    ("How are changes to production systems controlled?",
     "Through the IT change management process: changes are risk-assessed, approved by the Change "
     "Advisory Board (or under the emergency change procedure), tested and recorded.",
     "Change Management Procedure"),
    ("Are development and test environments kept separate from production?",
     "Yes. Development, test and production are separate environments. Live customer data is not "
     "used in test unless it has been anonymised.",
     "Secure Development Standard"),
    ("If you provide remote services, how do you connect to customer sites?",
     "Condition monitoring gateways at customer sites make outbound-only encrypted connections "
     "(TLS 1.2 or higher) to Kestrel's monitoring platform; no inbound ports are opened on the "
     "customer network. Where a customer allows engineer remote access, it uses the customer's own "
     "remote access service with named accounts and MFA.",
     "Remote Monitoring Security Description"),
    ("How are devices you install at customer sites secured?",
     "Gateways run a hardened Linux image with unused services disabled, secure boot and a unique "
     "device certificate. Firmware updates are signed, tested and deployed remotely at least every "
     "quarter.",
     "Gateway hardening standard; firmware release notes"),
    ("How do you manage information security risks from your suppliers?",
     "Suppliers with access to Kestrel or customer data complete a security assessment before "
     "contract and every two years. Contracts include security and confidentiality obligations "
     "and a right to audit.",
     "Supplier Security Procedure"),
    ("Do you use subcontractors to process customer data?",
     "Three: the colocation provider (UK data centres), the managed security service provider "
     "(24/7 monitoring) and the cloud hosting provider (UK regions). No other subcontractors "
     "process customer data.",
     "Subprocessor list"),
    ("Do you have an incident response plan?",
     "Yes. The Security Incident Response Plan sets out roles, severity levels and escalation. It "
     "is tested every year with a tabletop exercise; the last one was in April 2025.",
     "Security Incident Response Plan; exercise report April 2025"),
    ("How quickly would you tell us about an incident affecting our data?",
     "Without undue delay and in any case within 24 hours of confirming an incident affecting "
     "customer data or systems, with updates as the investigation progresses.",
     "Security Incident Response Plan"),
    ("Have you had a data breach in the last three years?",
     "No security incident involving customer data in the last three years. In 2024 a phishing "
     "email compromised one internal mailbox; it was contained the same day and no customer data "
     "was involved.",
     "Incident log"),
    ("Describe your backup arrangements.",
     "Daily incremental and weekly full backups, encrypted, with a copy held off-site and an "
     "immutable copy in the cloud. Restores are tested every quarter.",
     "Backup Standard; restore test records"),
    ("Do you have business continuity and disaster recovery plans?",
     "Yes. The business continuity plan covers manufacturing, IT and the remote monitoring "
     "service. The recovery time objective for the monitoring platform is 8 hours. Plans are "
     "tested every year; the last test was in May 2025.",
     "Business Continuity Plan; DR test report May 2025"),
    ("What insurance cover do you hold?",
     "Cyber insurance with a limit of GBP 5 million and product liability insurance with a limit "
     "of GBP 10 million, each for any one claim.",
     "Insurance certificates 2025"),
]

STANDARD_ANSWERS_FILE = "Kestrel_Security_Questionnaire_Responses_2025-09.docx"


def check_questionnaire_map():
    assert len(ACME_QUESTIONS) == 40 and len(PAST_QUESTIONNAIRE) == 40
    used = [p for p in QUESTIONNAIRE_MAP.values() if p]
    assert len(used) == 38 and len(set(used)) == 38, "38 distinct past answers expected"
    assert sorted(set(range(1, 41)) - set(used)) == [5, 28]
    assert [a for a, p in QUESTIONNAIRE_MAP.items() if p is None] == [39, 40]
    assert "SOC 2" in ACME_QUESTIONS[38] and "penetration test" in ACME_QUESTIONS[39]
    past_text = " ".join(q + " " + a for q, a, _ in PAST_QUESTIONNAIRE).lower()
    assert "soc 2" not in past_text and "penetration" not in past_text and "pen test" not in past_text

# ======================================================================= people

LEGAL = ("Kestrel Legal", "legal@kestrel-eng.co.uk")
ALEX = ("Alex Morgan", "alex.morgan@kestrel-eng.co.uk")
TOM = ("Tom Hale", "tom.hale@kestrel-eng.co.uk")
TOM_HOME = ("Tom Hale", "tomhale.home@gmail.com")
PRIYA = ("Priya Shah", "priya.shah@kestrel-eng.co.uk")
MARCUS = ("Marcus Reid", "marcus.reid@kestrel-eng.co.uk")
LENA = ("Lena Vogt", "lena.vogt@kestrel-eng.de")
DAN = ("Dan Ellis", "dan.ellis@kestrel-eng.co.uk")
EVENTS = ("Kestrel Events", "events@kestrel-eng.co.uk")
JULIA = ("Julia Schmidt", "j.schmidt@acme-automotive.de")
FELIX = ("Dr Felix Brandt", "f.brandt@acme-automotive.de")
ACME_SEC = ("Acme Supplier Security", "vendor-security@acme-automotive.de")
FAKE_FELIX = ("Dr Felix Brandt", "f.brandt@acme-automotlve.de")
OLIVIA = ("Olivia Grant", "olivia.grant@meridianbank.co.uk")
JONAS = ("Jonas Keller", "j.keller@voltarail.co.uk")
MARK = ("Mark Ostrow", "m.ostrow@haldenwater.co.uk")
NORTHGATE = ("Northgate Logistics Accounts", "accounts@northgate-logistics.com")
CARLOS = ("Carlos Mendes", "carlos.mendes@riobombas.com.br")
BRIGHTLAW = ("BrightLaw LLP", "news@brightlaw.co.uk")
FLOWTECH = ("FlowTech Seals", "marketing@flowtechseals.com")
PRINTHAUS = ("PrintHaus", "noreply@printhaus.de")

TOM_SIG = """Tom Hale
Key Account Manager
Kestrel Engineering Ltd
T +44 114 496 0412 | M +44 7700 900412
tom.hale@kestrel-eng.co.uk"""

ALEX_SIG = """Alex Morgan
Senior Legal Counsel
Kestrel Engineering Ltd
T +44 114 496 0230
alex.morgan@kestrel-eng.co.uk

This email may contain confidential and legally privileged information. If you have received it in error, please tell the sender and delete it."""

MARCUS_SIG = """Marcus Reid
Logistics and Export Compliance
Kestrel Engineering Ltd
T +44 114 496 0587
marcus.reid@kestrel-eng.co.uk"""

PRIYA_SIG = """Priya Shah
Bid Manager
Kestrel Engineering Ltd
T +44 114 496 0351 | M +44 7700 900351
priya.shah@kestrel-eng.co.uk"""

LENA_SIG = """Lena Vogt
Finance Manager
Kestrel Pumpen GmbH
Dortmund, Germany
lena.vogt@kestrel-eng.de"""

ACME_FOOTER = ("Acme Automotive GmbH | Registered office: Stuttgart | Commercial register: Stuttgart "
               "Local Court, HRB 000000 | Managing Directors: Dr Ingrid Vossberg, Peter Lindqvist")

JULIA_SIG = """Best regards

Julia Schmidt
Strategic Purchasing
Acme Automotive GmbH
Stuttgart, Germany
T +49 711 0815 2210
j.schmidt@acme-automotive.de

""" + ACME_FOOTER

FELIX_SIG = """Best regards

Dr Felix Brandt
Legal Counsel
Acme Automotive GmbH | Legal Department
T +49 711 0815 3340
f.brandt@acme-automotive.de

""" + ACME_FOOTER

# ======================================================================= attachments


def build_attachments(out):
    """Generate every attachment once into out/ and return {name: bytes}."""
    out.mkdir(parents=True, exist_ok=True)
    a = {}

    def keep(name, data):
        a[name] = data

    keep("Acme_Mutual_NDA_v1.docx", legal_docs.build_acme_nda_v1(out / "Acme_Mutual_NDA_v1.docx"))
    keep("Acme_Mutual_NDA_v1_Kestrel.docx",
         legal_docs.build_acme_nda_kestrel(out / "Acme_Mutual_NDA_v1_Kestrel.docx"))
    keep("Acme_Kestrel_NDA_signed.pdf", pdfs.build_signed_nda(out / "Acme_Kestrel_NDA_signed.pdf"))
    keep("Acme_MSA_v1.docx", legal_docs.build_msa("v1", out / "Acme_MSA_v1.docx"))
    keep("Acme_MSA_v1_Kestrel_markup.docx",
         legal_docs.build_msa("markup", out / "Acme_MSA_v1_Kestrel_markup.docx"))
    keep("Acme_MSA_v2.docx", legal_docs.build_msa("v2", out / "Acme_MSA_v2.docx"))
    keep("Acme_MSA_v3.docx", legal_docs.build_msa("v3", out / "Acme_MSA_v3.docx"))
    keep("PX-400_datasheet.pdf", pdfs.build_px400_datasheet(out / "PX-400_datasheet.pdf"))
    keep("Volta_Rail_Tender_Terms.pdf", pdfs.build_volta_tender(out / "Volta_Rail_Tender_Terms.pdf"))
    keep("Northgate_Invoice_4471.pdf", pdfs.build_northgate_invoice(out / "Northgate_Invoice_4471.pdf"))
    keep("Acme_Supplier_Security_Questionnaire.docx",
         legal_docs.build_acme_questionnaire(out / "Acme_Supplier_Security_Questionnaire.docx",
                                             ACME_QUESTIONS))
    keep("Halden_Water_NDA.docx", legal_docs.build_halden_nda(out / "Halden_Water_NDA.docx"))
    keep("Meridian_Liability_Schedule.docx",
         legal_docs.build_meridian_schedule(out / "Meridian_Liability_Schedule.docx"))
    keep("FlowTech_Catalogue_2027.pdf",
         pdfs.build_flowtech_catalogue(out / "FlowTech_Catalogue_2027.pdf"))
    keep("RioBombas_Distribution_Agreement_Draft.docx",
         legal_docs.build_riobombas(out / "RioBombas_Distribution_Agreement_Draft.docx"))
    keep("image001.png", images.acme_logo())
    keep("logo.png", images.printhaus_logo())
    keep("invite.ics", SUPPLIER_DAY_ICS.encode("ascii"))
    for name in ("image001.png", "logo.png", "invite.ics"):
        (out / name).write_bytes(a[name])
    return a


SUPPLIER_DAY_ICS = "\r\n".join([
    "BEGIN:VCALENDAR",
    "PRODID:-//Kestrel Engineering//Events calendar//EN",
    "VERSION:2.0",
    "METHOD:REQUEST",
    "BEGIN:VTIMEZONE",
    "TZID:Europe/London",
    "BEGIN:STANDARD",
    "DTSTART:19701025T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
    "TZOFFSETFROM:+0100",
    "TZOFFSETTO:+0000",
    "TZNAME:GMT",
    "END:STANDARD",
    "BEGIN:DAYLIGHT",
    "DTSTART:19700329T010000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
    "TZOFFSETFROM:+0000",
    "TZOFFSETTO:+0100",
    "TZNAME:BST",
    "END:DAYLIGHT",
    "END:VTIMEZONE",
    "BEGIN:VEVENT",
    "UID:supplier-day-2026@kestrel-eng.co.uk",
    "DTSTAMP:20261013T110000Z",
    "DTSTART;TZID=Europe/London:20261119T093000",
    "DTEND;TZID=Europe/London:20261119T160000",
    "SUMMARY:Supplier day 2026",
    "LOCATION:Training Centre\\, Kestrel Engineering\\, Sheffield",
    "ORGANIZER;CN=Kestrel Events:mailto:events@kestrel-eng.co.uk",
    "ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE;CN=Kestrel Legal:mailto:legal@k",
    " estrel-eng.co.uk",
    "DESCRIPTION:Presentations from key suppliers on their 2027 plans\\, factory",
    "  tour and supplier awards. Lunch is provided.",
    "SEQUENCE:0",
    "STATUS:CONFIRMED",
    "TRANSP:OPAQUE",
    "END:VEVENT",
    "END:VCALENDAR",
    ""])

# ======================================================================= emails


def mid(mail_id, zone, y, mo, d, h, mi, address):
    return message_id(mail_id, local(zone, y, mo, d, h, mi), address)


def build_mails(att):
    """All 28 .eml emails, in id order. b3-05 (the .msg) exists here only as quoted text."""
    m = {}

    def files(*names):
        out = []
        for n in names:
            ctype = DOCX if n.endswith(".docx") else PDF
            out.append((n, att[n], ctype))
        return out

    # ------------------------------------------------------------- batch 1
    m["b1-01"] = Mail(
        "b1-01", local(UK, 2026, 10, 12, 9, 12), TOM, [LEGAL],
        "Acme NDA for review before MSA talks", """
Hi Alex,

Acme Automotive have sent over their mutual NDA ahead of the supply agreement talks. We want to share drawings and pricing for the process and cooling-water pumps for their new paint shop, and for the monitoring service, so the NDA needs to be in place before our meeting with them on Thursday.

It is on Acme's paper. My contact is Julia Schmidt in Strategic Purchasing. She has asked for any comments by Wednesday so that they can sign this week.

Could you take a look? I have not changed anything.

Thanks,
Tom

""" + TOM_SIG, attachments=files("Acme_Mutual_NDA_v1.docx"), batch=1)

    m["b1-02"] = Mail(
        "b1-02", local(UK, 2026, 10, 12, 15, 40), ALEX, [TOM],
        "RE: Acme NDA for review before MSA talks", """
Hi Tom,

I have marked up Acme's NDA (attached). There are two changes, both shown as tracked changes with a comment explaining each one, so you can send it to Julia as it is:

1. Term (clause 8.1): Acme's draft keeps everything confidential for five years. I have reduced this to three years, with five years for trade secrets. That is our usual position.
2. Governing law (clause 12): changed from German law and the Stuttgart courts to English law and the English courts.

Everything else is fine. The NDA is genuinely mutual, the definition of confidential information is reasonable, and there is no non-compete or non-solicitation clause.

If Acme push back on either point, please come back to me before agreeing anything.

Best,
Alex

""" + ALEX_SIG, quote=m["b1-01"], quote_style="on",
        attachments=files("Acme_Mutual_NDA_v1_Kestrel.docx"),
        in_reply_to=[m["b1-01"].message_id], references=[m["b1-01"].message_id], batch=1)

    m["b1-03"] = Mail(
        "b1-03", local(DE, 2026, 10, 14, 11, 5), JULIA, [TOM],
        "Signed NDA - Acme Automotive / Kestrel Engineering", """
Dear Tom,

Thank you for sending Kestrel's comments on the NDA. Our legal department has accepted both changes: the three-year term (five years for trade secrets) and English law.

Please find attached the NDA signed by both parties. Kestrel's signature was added yesterday and our two signatures this morning, so this copy is fully executed. Please keep it for your records.

I will send our draft Master Supply Agreement separately so that we can start the commercial discussion.

""" + JULIA_SIG, cc=[LEGAL], html_alt=True, attachments=files("Acme_Kestrel_NDA_signed.pdf"),
        batch=1)

    m["b1-04"] = Mail(
        "b1-04", local(DE, 2026, 10, 15, 8, 47), JULIA, [TOM],
        "Acme Master Supply Agreement - draft for review", """
Dear Tom,

As discussed, please find attached the first draft of our Master Supply Agreement for the supply of process and cooling-water pumps, spare parts and your remote condition monitoring service.

The draft is based on Acme's standard terms for strategic suppliers. Please note in particular clause 10 (data protection and information security), because your monitoring service will connect to our plant networks, and clause 12 (liability).

I have copied Dr Felix Brandt from our legal department, who will handle the legal points, and your legal team.

We would appreciate Kestrel's comments by Friday 23 October, so that we can aim for signature in November.

""" + JULIA_SIG, cc=[LEGAL, FELIX], html_alt=True, logo=att["image001.png"],
        logo_cid="<image001.png@01DD5C3A.6F1E2B90>", html_note="Acme Automotive",
        attachments=files("Acme_MSA_v1.docx"), batch=1)

    m["b1-05"] = Mail(
        "b1-05", local(UK, 2026, 10, 15, 9, 30), TOM, [LEGAL],
        "FW: Acme Master Supply Agreement - draft for review", """
Alex,

Forwarding in case this is stuck in the legal@ queue. Clause 12 is the one that worries me: unlimited liability for any data breach, and 200% of the annual fees for everything else. The account matters a lot to us, but I do not want to promise anything we cannot insure.

Can we talk before you send comments? I am in the office all day tomorrow.

Tom

""" + TOM_SIG, quote=m["b1-04"], quote_style="fwd-outlook",
        attachments=files("Acme_MSA_v1.docx"), references=[m["b1-04"].message_id], batch=1)

    m["b1-06"] = Mail(
        "b1-06", local(UK, 2026, 10, 13, 14, 20), MARCUS, [LEGAL],
        "Export query: PX-400 pumps to Egypt - dual use?", """
Hi Alex,

We have an order from a new customer in Egypt for 12 PX-400 pumps, worth about GBP 186,000. The customer is Nilewater Contracting S.A.E. in Alexandria, a contractor building a municipal water treatment plant. We would ship from Sheffield in December.

Before I confirm the shipping date, can you tell me whether the PX-400 needs an export licence? The datasheet is attached. My reading of the dual-use list is that pumps are only controlled when the parts in contact with the liquid are made of corrosion-resistant materials, and the PX-400 is cast iron throughout. But I would like a legal view before we rely on that.

Two other points:
- The customer has asked us to ship through a freight forwarder in Jebel Ali (UAE) rather than direct to Alexandria.
- They have not yet returned our end-user statement.

Could you let me know by Friday if possible?

Thanks
Marcus

""" + MARCUS_SIG, attachments=files("PX-400_datasheet.pdf"), batch=1)

    m["b1-07"] = Mail(
        "b1-07", local(UK, 2026, 10, 15, 16, 2), ALEX, [MARCUS],
        "RE: Export query: PX-400 pumps to Egypt - dual use?", """
Hi Marcus,

Short answer: on the information you sent, the PX-400 is not a listed dual-use item, so the pumps do not need an export licence as such. But please do not ship until the two points below are closed.

Why it is not listed: the only entry that could apply is 2B350.i in the UK dual-use list (pumps for corrosive chemicals). It covers only multiple-seal and seal-less pumps in which every surface in contact with the liquid is made of specified corrosion-resistant materials, such as high-nickel alloys, titanium or fluoropolymers. The datasheet shows a single mechanical seal, a grey cast iron casing and a ductile iron impeller, with no alloy options, so the PX-400 falls outside that entry. Please keep a copy of the datasheet on the shipping file as the basis for the "no licence required" decision.

Before you ship:
1. End-user statement. We need it signed by Nilewater, naming the end use (the municipal water treatment plant) and confirming that the pumps will not be re-exported.
2. Routing through Jebel Ali. Shipping through a forwarder in the UAE for a customer in Alexandria is a recognised diversion pattern. Ask the customer why, and get the forwarder's full name and address. If the answer is not convincing, ship direct or come back to me.

Please also run the usual screening of Nilewater, the forwarder and the paying bank against the UK sanctions list. If anything suggests a military end use, or a link to chemical or other weapons, stop and call me: the end-use controls apply even when goods are not listed.

Unless the end-user statement or the routing raises something new, I do not need to see this again.

Best,
Alex

""" + ALEX_SIG, quote=m["b1-06"], quote_style="on",
        in_reply_to=[m["b1-06"].message_id], references=[m["b1-06"].message_id], batch=1)

    m["b1-08"] = Mail(
        "b1-08", local(UK, 2026, 10, 14, 10, 15), PRIYA, [LEGAL],
        "Volta Rail RFQ - tender terms review (bid due 30 Oct)", """
Hi Alex,

Volta Rail have issued their invitation to tender for depot drainage, wash-plant and cooling-water pumps (ITT VR-T-2026-117). Bids are due at 12:00 on Friday 30 October.

The tender pack includes their contract terms, attached (40 pages). Bidders have to list any exceptions to the terms in the compliance form at Appendix D, and Volta say they will score exceptions down, so I only want to raise the ones that really matter.

From a quick read, the liability section and the IP and warranty section worry me most, but I am not a lawyer. Could you review the terms and send me a short list of the exceptions we must take, by Thursday 22 October? That gives me a week to price them in.

The estimated contract value is GBP 2.1m over five years, including maintenance.

Thanks
Priya

""" + PRIYA_SIG, attachments=files("Volta_Rail_Tender_Terms.pdf"), batch=1)

    northgate = Mail(
        "northgate-4471", local(UK, 2026, 10, 15, 16, 42), NORTHGATE, [LENA],
        "Northgate Logistics - invoice 4471 short payment", """
Dear Ms Vogt,

Our records show a payment of EUR 15,840.00 received on 25 September 2026 against invoice 4471 dated 31 August 2026 for EUR 18,640.00. A balance of EUR 2,800.00 remains outstanding.

We have no record of agreeing a deduction for damaged goods. Under clause 14 of our standard trading conditions, any claim for loss of or damage to goods in transit must be notified in writing within 7 days of delivery, and under clause 18 claims may not be set off against our charges.

Please arrange payment of the balance within 7 days of this email. If we do not receive payment, we will charge interest under our terms and may place your account on stop, which would affect the collections booked for November.

Kind regards

Accounts Receivable
Northgate Logistics Ltd
accounts@northgate-logistics.com""")

    m["b1-09"] = Mail(
        "b1-09", local(DE, 2026, 10, 16, 8, 55), LENA, [LEGAL],
        "WG: Northgate Logistics - invoice 4471 short payment", """
Hallo Alex,

I am forwarding an email from Northgate Logistics about their invoice 4471 (attached). We paid it short in September because two pallets of impellers arrived damaged in the August shipment to Dortmund, and we deducted the value of the damaged parts, EUR 2,800.00. Northgate now say the deduction was never agreed, and they will put our account on stop if we do not pay the balance within 7 days.

Can you tell me how to answer them? I am not sure whether this is a legal question or one for procurement, but I did not want to ignore it.

Viele Grüße / Kind regards
Lena

""" + LENA_SIG, quote=northgate, quote_style="fwd-de",
        attachments=files("Northgate_Invoice_4471.pdf"), batch=1)

    m["b1-10"] = Mail(
        "b1-10", local(UK, 2026, 10, 12, 7, 30), BRIGHTLAW, [LEGAL],
        "Autumn employment law update", """
BrightLaw LLP | Employment Update | Autumn 2026

View this email in your browser: https://news.brightlaw.co.uk/autumn-2026

In this issue
1. The 2026–27 reform timetable: what is in force and what comes next
2. Flexible working: refusing a request after the reforms
3. Holiday pay and record-keeping: what an audit should cover
4. Preventing sexual harassment: updating your policy and training
5. Webinar: our annual employment law review, Thursday 26 November 2026, 10:00

1. The reform timetable
Several of the reforms announced last year are now in force, and more are due in 2027. Our updated timeline sets out each change, when it takes effect and what employers should do first. Most employers will save time by reviewing contracts, policies and manager training together rather than one change at a time.

2. Flexible working
Employers can still refuse a flexible working request for a business reason, but under the reforms they will also need to show that the refusal is reasonable. We look at what a well-documented decision looks like, and the questions managers should ask before saying no.

3. Holiday pay and record-keeping
Tribunals expect employers to keep adequate records of working time and holiday. We set out the records to keep, for how long, and the gaps we most often find in audits.

4. Preventing sexual harassment
Every employer is under a duty to take reasonable steps to prevent sexual harassment of its workers. Our short checklist covers your policy, reporting routes and training.

5. Webinar
Join our employment team for a one-hour review of the year, with time for questions. Register at https://news.brightlaw.co.uk/webinar-2026

BrightLaw LLP is a limited liability partnership registered in England and Wales and authorised and regulated by the Solicitors Regulation Authority. This update is general information, not legal advice.

You are receiving this email because you subscribed to BrightLaw updates. Unsubscribe: https://news.brightlaw.co.uk/unsubscribe?u=kestrel-legal""",
        html_alt=True, batch=1, extra_headers=[
            ("List-Unsubscribe", "<mailto:unsubscribe@brightlaw.co.uk?subject=unsubscribe>, "
                                 "<https://news.brightlaw.co.uk/unsubscribe?u=kestrel-legal>"),
            ("List-Unsubscribe-Post", "List-Unsubscribe=One-Click"),
            ("Precedence", "bulk")])

    m["b1-11"] = Mail(
        "b1-11", local(UK, 2026, 10, 13, 12, 0), EVENTS, [LEGAL],
        "Invitation: Supplier day 2026", """
You are invited to Kestrel's Supplier day 2026.

When: Thursday 19 November 2026, 09:30 to 16:00 (UK time)
Where: Training Centre, Kestrel Engineering, Sheffield

Our key suppliers will present their 2027 plans, followed by a factory tour and the supplier awards. Lunch is provided. Please accept or decline this invitation so that we can confirm numbers for catering by 6 November.

Kestrel Events
events@kestrel-eng.co.uk""",
        calendar=SUPPLIER_DAY_ICS, attachments=[("invite.ics", att["invite.ics"], "application/ics")],
        batch=1)

    m["b1-12"] = Mail(
        "b1-12", local(UK, 2026, 10, 16, 10, 40), ALEX, [JULIA],
        "Acme MSA - Kestrel comments on clause 12 (liability)", """
Dear Julia, dear Felix,

Thank you for the draft Master Supply Agreement. Ahead of our full comments next week, I attach Kestrel's mark-up of clause 12 (liability), because it is the point most likely to need discussion. The changes are tracked and each one has a comment explaining it. In summary:

1. General cap: 100% of the Annual Fees, instead of 200%. This reflects the value of the supply and market practice for equipment of this kind.
2. Data breach: Kestrel cannot accept unlimited liability. We propose a separate cap of two times the Annual Fees for data breach and breaches of clause 10, in addition to the general cap.
3. Indirect loss: we have replaced Kestrel's liability for indirect and consequential loss, including loss of production, with a mutual exclusion. Unlimited exposure to production stoppage costs is not insurable for an equipment supplier.

The carve-outs in clause 12.3 (injury to life, body or health; intent and gross negligence; product liability; guarantees) stay as they are.

We are happy to discuss this on a call. Tom will suggest some times.

Kind regards
Alex

""" + ALEX_SIG, cc=[FELIX, TOM], quote=m["b1-04"], quote_style="on",
        attachments=files("Acme_MSA_v1_Kestrel_markup.docx"),
        in_reply_to=[m["b1-04"].message_id], references=[m["b1-04"].message_id], batch=1)

    # ------------------------------------------------------------- batch 2
    m["b2-01"] = Mail(
        "b2-01", local(DE, 2026, 10, 19, 9, 5), FELIX, [ALEX],
        "RE: Acme MSA - Kestrel comments on clause 12 (liability) [{{REF:G02}}]", """
Dear Alex,

Thank you for Kestrel's mark-up of clause 12, which we have discussed with our purchasing and risk colleagues. Our revised draft (v2) is attached. In short:

1. General cap: we cannot go down to 100%. As a compromise we offer 150% of the Annual Fees.
2. Data breach: this must remain uncapped. Kestrel's monitoring service will connect to our plant networks, and under our group policy every supplier with network access accepts unlimited liability for data breaches. We are not able to deviate from this.
3. Indirect loss: we accept a mutual exclusion of indirect and consequential loss. However, costs of production stoppage caused by defective products are direct loss for us and must remain recoverable within the cap.

Please let us know whether Kestrel can accept this. We would like to finalise clause 12 this week.

As requested, we have added your reference {{REF:G02}} to the subject line.

""" + FELIX_SIG, cc=[JULIA, TOM], quote=m["b1-12"], quote_style="am", html_alt=True,
        logo=att["image001.png"], logo_cid="<image001.png@01DD5F7B.2A4C9D10>",
        html_note="Acme Automotive", attachments=files("Acme_MSA_v2.docx"),
        in_reply_to=[m["b1-12"].message_id],
        references=[m["b1-04"].message_id, m["b1-12"].message_id], batch=2)

    m["b2-02"] = Mail(
        "b2-02", local(DE, 2026, 10, 19, 11, 30), ACME_SEC, [TOM],
        "Supplier information security questionnaire - Kestrel Engineering (due 30 Oct)", """
Dear Mr Hale,

As part of onboarding Kestrel Engineering Ltd as a strategic supplier with access to Acme production networks (remote condition monitoring), Acme Automotive requires a completed supplier information security questionnaire.

Please answer all 40 questions in the attached form. For each answer, please name the supporting evidence (policy, certificate or report) and be ready to provide it on request. Where a question does not apply, please explain why.

Please return the completed questionnaire to vendor-security@acme-automotive.de by Friday 30 October 2026. Under clause 10.2 of the draft Master Supply Agreement, the monitoring service cannot be connected to our networks until the assessment is complete.

If you have questions about the form, please reply to this email and quote your supplier name.

Kind regards

Supplier Security Team
Information Security Office
Acme Automotive GmbH
vendor-security@acme-automotive.de

""" + ACME_FOOTER, cc=[LEGAL], html_alt=True,
        attachments=files("Acme_Supplier_Security_Questionnaire.docx"), batch=2)

    m["b2-03"] = Mail(
        "b2-03", local(UK, 2026, 10, 20, 10, 10), MARCUS, [LEGAL],
        "RE: Export query: PX-400 pumps to Egypt - dual use? [{{REF:G03}}]", """
Hi Alex,

Picking this up again under your reference {{REF:G03}}.

The end-user statement came back signed on Friday, the customer explained the routing (their forwarder consolidates loads for Alexandria), and the screening was clear. But Nilewater have now asked for 4 of the 12 pumps in a corrosion-resistant version, because they will be pumping brine from a new desalination stage.

Engineering say they can build these as a special: a super-austenitic stainless steel casing and impeller (roughly 25% nickel and 20% chromium; I am waiting for the exact grade) and a double mechanical seal. The other 8 pumps stay as standard cast iron.

Does that change your advice? If we need a licence, how long would it take? The customer still wants everything delivered in December.

Thanks
Marcus

""" + MARCUS_SIG, quote=m["b1-07"], quote_style="on",
        in_reply_to=[m["b1-07"].message_id],
        references=[m["b1-06"].message_id, m["b1-07"].message_id], batch=2)

    m["b2-04"] = Mail(
        "b2-04", local(UK, 2026, 10, 20, 14, 45), MARK, [TOM],
        "Halden Water - NDA for Thornbury pumping station project", """
Dear Tom,

Thank you for your interest in the Thornbury pumping station upgrade. Before we can share the hydraulic models and site surveys, we need Kestrel to sign our standard confidentiality agreement, which is attached.

Please return a signed copy by Friday 30 October so that we can include Kestrel in the early supplier engagement sessions starting in November. Our agreement is not normally open to negotiation, but please let me know if you have any questions.

Kind regards,

Mark Ostrow
Procurement Manager, Capital Delivery
Halden Water Ltd
T +44 1632 960214""", cc=[LEGAL], html_alt=True, attachments=files("Halden_Water_NDA.docx"),
        batch=2)

    m["b2-05"] = Mail(
        "b2-05", local(UK, 2026, 10, 21, 9, 20), OLIVIA, [TOM],
        "Meridian Bank - maintenance contract liability schedule", """
Dear Tom,

Further to our meeting last week, please find attached Schedule 7 (Limitation of Liability) for the maintenance contract covering the pumping and cooling plant at our two data centres.

As a PRA-regulated firm, we have to meet our regulators' expectations on outsourcing and third-party risk. The schedule therefore includes a higher cap for data breach (three times the annual charges) and makes the supplier liable without limit for regulatory fines that result from the supplier's default. These are standard requirements for our material suppliers.

We need your comments by Wednesday 4 November, so that the contract can go to our supplier risk committee on 11 November.

Kind regards

Olivia Grant
Supplier Management | Procurement
Meridian Bank plc
T +44 20 7946 0731

Meridian Bank plc is authorised by the Prudential Regulation Authority and regulated by the Financial Conduct Authority and the Prudential Regulation Authority. Registered in England and Wales. This email and any attachments are confidential.""",
        cc=[LEGAL], html_alt=True, attachments=files("Meridian_Liability_Schedule.docx"), batch=2)

    m["b2-06"] = Mail(
        "b2-06", local(DE, 2026, 10, 21, 16, 5), JULIA, [LEGAL], "Quick question", """
Hello,

quick question: who on your side signs off on this, you or Tom? We would like to have everything closed by the end of the month.

Thanks
Julia

Sent from my mobile""", batch=2)

    m["b2-07"] = Mail(
        "b2-07", local(UK, 2026, 10, 19, 10, 2), JONAS, [PRIYA],
        "Out of office: Jonas Keller until 2 November", """
Thank you for your email. I am out of the office until Monday 2 November 2026 with limited access to email.

For questions about the depot pumps tender (ITT VR-T-2026-117), please use the clarification facility in the tender portal or write to tenders@voltarail.co.uk. The deadline for clarification questions is 12:00 on 23 October.

For other urgent procurement matters, please call the procurement team on +44 1632 960400.

Jonas Keller
Procurement, Volta Rail Ltd""", cc=[LEGAL],
        in_reply_to=["<priya-clarification.202610190955@kestrel-eng.co.uk>"],
        references=["<priya-clarification.202610190955@kestrel-eng.co.uk>"],
        extra_headers=[("Auto-Submitted", "auto-replied"), ("X-Auto-Response-Suppress", "All")],
        batch=2)

    m["b2-08"] = Mail(
        "b2-08", local(UK, 2026, 10, 22, 8, 0), FLOWTECH, [LEGAL],
        "New 2027 catalogue: mechanical seals for water pumps", """
Dear Sir or Madam,

Our 2027 catalogue is here. It covers our full range of mechanical seals for clean water and wastewater pumps, including the new FT-Cartridge 50 series for end-suction pumps up to 16 bar.

Highlights:
- Cartridge seals for shaft sizes from 25 to 100 mm
- Silicon carbide and tungsten carbide face options
- Drinking-water approved elastomers
- Next-day dispatch from our UK warehouse on more than 400 stock items

The catalogue is attached as a PDF. Order before 31 December 2026 and receive 10% off your first order with code CAT2027.

Best regards,
The FlowTech Seals team
marketing@flowtechseals.com

To stop receiving these emails, reply with "unsubscribe" in the subject line.""",
        html_alt=True, attachments=files("FlowTech_Catalogue_2027.pdf"), batch=2)

    m["b2-09"] = Mail(
        "b2-09", local(UK, 2026, 10, 22, 17, 15), ALEX, [PRIYA],
        "RE: Volta Rail RFQ - tender terms review (bid due 30 Oct) [{{REF:G04}}]", """
Hi Priya,

I have been through Volta's terms. Most of the 40 pages are standard and we can comply. Two pages matter: page 23 (section 21, Liability) and page 31 (section 29, Intellectual property and warranty). These are the five exceptions I recommend for the compliance form at Appendix D, in order of importance:

1. Consequential loss (clause 21.3, page 23). Volta want unlimited liability for indirect and consequential loss, including lost revenue and the penalties they pay to train operators. We cannot accept this. Proposed wording: "Neither party shall be liable for any indirect or consequential loss, or for any loss of profit, revenue or use, however arising."

2. Overall cap (clause 21.1, page 23). The terms put no cap on our liability. Propose a cap of 100% of the charges paid or payable in the 12 months before the claim, which is our standard position, with the usual exceptions for death or personal injury and fraud.

3. Liquidated damages (clause 21.5, page 23). A cap of 20% of the whole contract price is high, and the damages are not Volta's only remedy for delay. Propose 10% of the price of the delayed goods, with liquidated damages as Volta's sole remedy for delay.

4. Background IP (clause 29.2, page 31). Volta want an assignment of all IP in the deliverables, including our background IP. Propose instead that Kestrel keeps its background IP and grants Volta a non-exclusive, royalty-free licence to use it to operate, maintain and repair the pumps.

5. Warranty (clause 29.6, page 31). Thirty-six months from acceptance is longer than our standard terms. Propose 24 months from acceptance if you are willing to price the extra cover; otherwise our standard warranty.

Please do not list anything else as an exception. The rest can be accepted, raised as clarification questions before the deadline at 12:00 tomorrow, or dealt with in the price, for example the cost of the 10% performance bond in section 24.

If Volta reject exception 1 or 4, please come back to me before you confirm the bid. Those are the two I would walk away on.

Our ref: {{REF:G04}}

Best,
Alex

""" + ALEX_SIG, quote=m["b1-08"], quote_style="on",
        in_reply_to=[m["b1-08"].message_id], references=[m["b1-08"].message_id], batch=2)

    # ------------------------------------------------------------- batch 3
    m["b3-01"] = Mail(
        "b3-01", local(UK, 2026, 10, 26, 7, 45), TOM_HOME, [ALEX], "RE: Acme MSA [{{REF:G02}}]", """
Alex,

Sending this from my personal email because my laptop is in for repair until Wednesday.

Julia called me on Friday evening. Acme's purchasing board meets on 4 November and they want clause 12 settled before then. She hinted that Felix might move on data breach if we move on the general cap. Could we offer 150% on the general cap if they accept a cap on data breach? I know the CFO has to approve anything above 100%.

Can we talk this morning? I am on my mobile all day: 07700 900412.

Tom""", batch=3)

    m["b3-02"] = Mail(
        "b3-02", local(DE, 2026, 10, 27, 10, 30), FELIX, [ALEX],
        "RE: Acme MSA - Kestrel comments on clause 12 (liability) [{{REF:G02}}]", """
Dear Alex,

Thank you for the call on Friday. As promised, I attach v3 of the Master Supply Agreement with a revised clause 12:

1. General cap: 150% of the Annual Fees, unchanged from v2.
2. Data breach: we have moved. Kestrel's liability for a data breach will be unlimited only where the breach is caused by Kestrel's gross negligence or wilful misconduct. All other data breach claims fall under the general cap of 150%.
3. Indirect loss: as in v2.

This is as far as we can go. Our purchasing board meets on 4 November and we would like to present an agreed clause 12. Please confirm by Friday 30 October whether Kestrel can accept v3.

""" + FELIX_SIG, cc=[JULIA, TOM], quote=m["b2-01"], quote_style="am", html_alt=True,
        logo=att["image001.png"], logo_cid="<image001.png@01DD65D2.7B3E1A40>",
        html_note="Acme Automotive", attachments=files("Acme_MSA_v3.docx"),
        in_reply_to=[m["b2-01"].message_id],
        references=[m["b1-04"].message_id, m["b1-12"].message_id, m["b2-01"].message_id], batch=3)

    m["b3-03"] = Mail(
        "b3-03", local(DE, 2026, 10, 27, 13, 2), FAKE_FELIX, [ALEX],
        "RE: Acme MSA [{{REF:G02}}] - urgent: signing and payment details", """
Dear Alex,

Further to my email of this morning, our management has now approved the final version of the Master Supply Agreement. To meet our month-end deadline, please send me the signature page signed by Kestrel's authorised signatory today, as a PDF to this address. We will countersign and return the fully executed copy.

Separately, our finance department has asked me to let you know that Acme Automotive's bank details for supplier rebates and quality debit notes changed with effect from 26 October 2026. Please make sure your accounts team uses the new account below for the rebate settlement due this week, and confirm by return once your records are updated:

Account name: Acme Automotive GmbH
IBAN: DE00 1000 0000 0000 4417 92
BIC: ZZZZDEFFXXX

Please treat this as urgent and confidential. I am travelling and can only be reached by email today, so please do not call. Julia is out of the office this week, so there is no need to copy her.

Best regards

Dr Felix Brandt
Legal Counsel
Acme Automotive GmbH | Legal Department
f.brandt@acme-automotive.de

""" + ACME_FOOTER, from_header='"Dr Felix Brandt" <f.brandt@acme-automotlve.de>',
        extra_headers=[("X-Priority", "1 (Highest)"), ("Importance", "High")], batch=3)

    m["b3-04"] = Mail(
        "b3-04", local(UK, 2026, 10, 28, 15, 20), CARLOS, [TOM],
        "Exclusive distribution agreement - Brazil", """
Dear Tom,

It was a pleasure to meet you at the trade fair in São Paulo last month. As we discussed, Rio Bombas would like to become Kestrel's exclusive distributor for Brazil.

Please find attached our draft distribution agreement. The key points are:
- exclusive rights for the whole of Brazil, including sales to OEMs, EPC contractors and the state water and sanitation companies;
- minimum purchase targets of EUR 400,000 in the first year, rising to EUR 900,000 in the third year;
- an initial term of five years;
- Brazilian law, with the courts of São Paulo.

We would be grateful for your comments by 13 November, so that we can sign before the end of the year and start marketing in January.

Atenciosamente / Kind regards,

Carlos Mendes
Diretor Comercial / Commercial Director
Rio Bombas Distribuição Ltda
São Paulo, SP, Brasil
T +55 11 0123 4567""", cc=[LEGAL], html_alt=True,
        attachments=files("RioBombas_Distribution_Agreement_Draft.docx"), batch=3)

    lena_b305 = Mail(
        "b3-05", local(DE, 2026, 10, 28, 9, 10), LENA, [LEGAL],
        "Vollmacht / PoA for Kestrel Pumpen GmbH - who can sign?", B305_BODY)

    m["b3-06"] = Mail(
        "b3-06", local(UK, 2026, 10, 29, 11, 11), ALEX, [LENA],
        "RE: Vollmacht / PoA for Kestrel Pumpen GmbH - who can sign?", """
Hi Lena,

Thanks for the clear summary. Answers below.

1. Who signs: the Vollmacht has to be signed for the GmbH by both Geschäftsführer, Jens Hartmann and Helen Ashworth, acting together, because that is how the company's power of representation is entered in the Handelsregister. One signature is not enough, even on a bank form, and the bank will check the signatures against the Handelsregisterauszug it already has. Chris cannot sign: he is not a Geschäftsführer of the GmbH, and his role as group CFO is with Kestrel Engineering Ltd, the shareholder, which gives him no power to represent the GmbH. His part is to approve: under our delegation of authority policy, a new bank account and any Kontovollmacht need the CFO's approval before the Geschäftsführer sign. Please ask him to confirm his approval by email.

2. Notarisation: no. A Kontovollmacht does not need a notary under German law. The bank will check the signatories against the register and their ID. A notary is only needed for things like filings with the Handelsregister or property transactions.

Please send me the bank's form before Jens and Helen sign it. I want to check the scope: which accounts it covers, whether there is an amount limit, and that payments need you and your colleague together, not one of you alone, which is how payment release works in the GmbH today.

If the form is fine, Jens and Helen can sign it in time for the bank's deadline on 6 November. Helen is based in Sheffield, so I can get her signature here and send the form on to Jens in Dortmund.

If you will regularly need to sign for the GmbH beyond the bank, we could look at Prokura instead. That is a different route, and it is entered in the Handelsregister through a notary.

Best,
Alex

""" + ALEX_SIG, quote=lena_b305, quote_style="on",
        in_reply_to=[lena_b305.message_id], references=[lena_b305.message_id], batch=3)

    m["b3-07"] = Mail(
        "b3-07", local(UK, 2026, 10, 29, 14, 30), DAN, [LEGAL], "Personal - advice please", """
Hi,

I hope it is all right to email this address. I did not know who else to ask, and I would rather not go to HR yet.

I was signed off sick for three weeks in September with stress. Since I came back, my manager, Neil Garside, has taken me off the planning team's overtime rota and keeps making comments in front of the team about people who "can't hack it". At my return-to-work meeting he said my absence would be "taken into account" at my next review, and I am worried this means I am being lined up to go.

I am thinking about raising a formal grievance, but I do not want to make things worse. Can someone tell me what my options are, and whether anything I say to you stays confidential?

Thanks,
Dan Ellis
Production Planner""", batch=3)

    m["b3-08"] = Mail(
        "b3-08", local(UK, 2026, 10, 30, 6, 0), PRINTHAUS, [LEGAL], "", "PrintHaus",
        html_alt=True, logo=att["logo.png"], logo_cid="<logo.png@printhaus.de>",
        logo_layout="related-inner", html_note="PrintHaus", batch=3)
    return m


B305_BODY = """Hallo zusammen,

we are opening a new business account (Geschäftskonto) for Kestrel Pumpen GmbH with our Hausbank here in Dortmund. It is for the service business, so that the payments under the maintenance contracts come in separately from the pump sales.

The bank has sent us their standard Kontovollmacht. With it, the GmbH authorises me and one colleague from accounts to operate the account and to release payments in online banking. According to the bank, the form must be signed "by the persons who represent the company according to the commercial register (Handelsregister)".

Two questions, please:

1. Who at Kestrel can sign the Vollmacht for the GmbH? I think both Geschäftsführer have to sign together, but I am not sure if one signature is enough for a bank form. Chris Barker also offered to sign for the group as CFO. Is that possible, or must it be the Geschäftsführer?

2. Does the Vollmacht have to be notarised (notariell beglaubigt)? When the GmbH was founded, everything went through the notary, so I do not know what is really needed for a bank form like this.

The bank would like the signed form back by Friday, 6 November. They already have our current Handelsregisterauszug and the Gesellschafterliste.

I can forward the bank's form and their email if you need them.

Vielen Dank und viele Grüße
Lena

Lena Vogt
Finance Manager
Kestrel Pumpen GmbH
Dortmund, Germany
lena.vogt@kestrel-eng.de"""

B305_FILE = "Vollmacht PoA for Kestrel Pumpen GmbH - who can sign.msg"
B305_ID = mid("b3-05", DE, 2026, 10, 28, 9, 10, "lena.vogt@kestrel-eng.de")

# ======================================================================= expected.csv
#
# Columns (spec G): id,batch,file,message_id,kind,group,area,sub_area,subject,proposed_outcome,
# flags,tests. Alternatives are separated by '|'. message_id is without angle brackets.
# kind: matter | noise | please-check (b2-06: please-check|matter, accepted in G02 after the
# human re-files it). group: Gxx; for a please-check row, the matter its note should name
# (b2-06: G02|G06, the first is where the human files it).
# proposed_outcome: alternatives for the matter's proposed outcome after this email; the
# checker uses the latest email of each group in the batches dropped so far.
# flags: ';' separates flags that must all be present, '|' alternatives. follows:Gxx checks the
# matter's follows field, label:X its label. Checked as warnings (failures with --strict).

ACME = "acme-automotive|acme"
OUT_ALL = "in_progress|ready_for_lawyer|nothing_needed"

EXPECT = {
    "b1-01": ("matter", "G01", "commercial", "customers", ACME, "ready_for_lawyer", "",
              "new matter and new subject folder from an internal request; NDA on the "
              "customer's paper"),
    "b1-02": ("matter", "G01", "commercial", "customers", ACME, OUT_ALL, "",
              "our reply (out) files by In-Reply-To b1-01; mark-up goes to documents/ours/ and "
              "is read as tracked changes and comments"),
    "b1-03": ("matter", "G01", "commercial", "customers", ACME, "ready_for_lawyer|nothing_needed",
              "", "no tag and no thread headers: candidate match on subject and topic (the signed "
              "NDA belongs to G01)"),
    "b1-04": ("matter", "G02", "commercial", "customers", ACME, "ready_for_lawyer", "follows:G01",
              "new matter under the same subject that follows G01; inline signature logo "
              "image001.png recorded as read=no and not stored"),
    "b1-05": ("matter", "G02", "commercial", "customers", ACME, "ready_for_lawyer|in_progress", "",
              "internal forward files by References b1-04; Acme_MSA_v1.docx is byte-identical: "
              "one copy stored, second row duplicate_of"),
    "b1-06": ("matter", "G03", "trade-compliance", "exports",
              "px-400|px-400-pumps|px400|egypt", "ready_for_lawyer", "",
              "new matter in trade-compliance/exports, subject by product or destination; 2-page "
              "datasheet read"),
    "b1-07": ("matter", "G03", "trade-compliance", "exports",
              "px-400|px-400-pumps|px400|egypt", "nothing_needed|in_progress|"
              "ready_for_lawyer", "", "our answer (out) files by In-Reply-To b1-06"),
    "b1-08": ("matter", "G04", "commercial", "customers", "volta-rail|volta", "ready_for_lawyer", "",
              "40-page PDF read by its contents page and the two pages that matter (p.23 "
              "liability, p.31 IP and warranty); bid due 30 Oct"),
    "b1-09": ("matter", "G05", "general", "", "unfiled", "out_of_area", "out-of-area|general-flagged",
              "misdirected accounts-payable dispute forwarded in German (WG:) with the supplier's "
              "text inside: general/unfiled, out_of_area with a suggested home"),
    "b1-10": ("noise", "", "", "", "", "nothing_needed", "",
              "newsletter with List-Unsubscribe and Precedence: bulk"),
    "b1-11": ("noise", "", "", "", "", "nothing_needed", "",
              "calendar invitation (text/calendar part and invite.ics); calendar parts never "
              "stored"),
    "b1-12": ("matter", "G02", "commercial", "customers", ACME, "in_progress|ready_for_lawyer", "",
              "our clause 12 mark-up to Acme (out) files by In-Reply-To b1-04 despite a new "
              "subject; tracked changes and comments read"),
    "b2-01": ("matter", "G02", "commercial", "customers", ACME, "in_progress|ready_for_lawyer", "",
              "tag + counterparty on the roster (roster-address); also thread match on b1-12; v2 "
              "recorded as a version of the MSA"),
    "b2-02": ("matter", "G06", "commercial", "customers", ACME,
              "needs_info_from_requester|ready_for_lawyer", "",
              "sibling matter under the same subject, not G02; 38 of 40 questions answerable "
              "from knowledge/standard-answers, 2 need IT Security"),
    "b2-03": ("matter", "G03", "trade-compliance", "exports",
              "px-400|px-400-pumps|px400|egypt",
              "ready_for_lawyer|needs_info_from_requester|in_progress", "reopened",
              "tag + internal sender on a matter closed after batch 1: reopened"),
    "b2-04": ("matter", "G07", "commercial", "customers", "halden-water|halden", "ready_for_lawyer",
              "", "second customer's NDA: one-way, 5-year term, clause 9 two-year regional "
              "non-compete; read with the drafted nda-review skill"),
    "b2-05": ("matter", "G08", "commercial", "customers", "meridian-bank|meridian",
              "ready_for_lawyer", "", "regulated bank: 3x data-breach cap fits the PRA/FCA "
              "exception with CFO approval; uncapped regulatory fines do not"),
    "b2-06": ("please-check|matter", "G02|G06", "commercial", "customers", ACME, "", "",
              "ambiguous: no tag, no thread, two open Acme matters -> please-check, note names "
              "G02 and G06; after the human files it into G02 it is accepted there"),
    "b2-07": ("noise", "", "", "", "", "nothing_needed", "",
              "out-of-office (Auto-Submitted: auto-replied) in reply to an id in no file"),
    "b2-08": ("noise", "", "", "", "", "nothing_needed", "",
              "supplier brochure with a 4-page PDF and no bulk headers: noise by reading"),
    "b2-09": ("matter", "G04", "commercial", "customers", "volta-rail|volta", OUT_ALL, "",
              "our reply (out) with the five exceptions: tag + internal sender, and In-Reply-To "
              "b1-08"),
    "b3-01": ("matter", "G02", "commercial", "customers", ACME, "in_progress|ready_for_lawyer",
              "personal-address", "tag from a personal mailbox: roster name + free-mail "
              "(roster-name-freemail) -> files, alias added, flag personal-address"),
    "b3-02": ("matter", "G02", "commercial", "customers", ACME, "ready_for_lawyer", "",
              "same file name as b2-01 dropped again; v3 recorded, superseded facts get new lines"),
    "b3-03": ("please-check", "G02", "", "", "", "", "possible-impersonation",
              "tag from a lookalike domain with a roster name (roster-name-other-domain) -> "
              "please-check, claimed G02; no action on the bank details or the signing request"),
    "b3-04": ("matter", "G10", "commercial", "", "rio-bombas|riobombas|rio-bombas-distribuicao",
              "ready_for_lawyer", "proposed-sub-area:distributors|proposed-sub-area:distribution",
              "needs a sub-area that does not exist: matter under areas/commercial/rio-bombas/, "
              "sub-area proposed in the digest, not created"),
    "b3-05": ("matter", "G09", "corporate", "",
              "signing-authority|power-of-attorney|kestrel-pumpen-gmbh|poa|vollmacht|"
              "authorised-signatories", "needs_info_from_requester|ready_for_lawyer", "",
              "the one .msg: converted with msg2eml, .msg and .eml kept side by side"),
    "b3-06": ("matter", "G09", "corporate", "",
              "signing-authority|power-of-attorney|kestrel-pumpen-gmbh|poa|vollmacht|"
              "authorised-signatories", "needs_info_from_requester|in_progress|ready_for_lawyer",
              "", "our reply (out) files by In-Reply-To the converted .msg's Message-ID"),
    "b3-07": ("matter", "G11", "general", "", "unfiled", "needs_lawyer", "sensitive;label:hr-personal",
              "HR-personal: recognised only; general/unfiled sensitive topic, needs_lawyer; no "
              "facts, roster or summary from the contents"),
    "b3-08": ("noise", "", "", "", "", "nothing_needed", "",
              "empty subject and an inline logo only (logo-only, empty-body); logo not stored"),
}

COLUMNS = ["id", "batch", "file", "message_id", "kind", "group", "area", "sub_area", "subject",
           "proposed_outcome", "flags", "tests"]


def batch_names(mails):
    """{id: file name} with the Outlook rule and ' (2)' for a repeat inside one batch."""
    names = {}
    for batch in (1, 2, 3):
        taken = {B305_FILE.lower()} if batch == 3 else set()
        for mail_id in sorted(k for k, v in mails.items() if v.batch == batch):
            name = outlook_file_name(mails[mail_id].subject)
            stem = name[:-4]
            n = 2
            while name.lower() in taken:
                name = "%s (%d).eml" % (stem, n)
                n += 1
            taken.add(name.lower())
            names[mail_id] = name
    return names


def expected_rows(mails, names):
    rows = []
    for mail_id in sorted(EXPECT):
        kind, group, area, sub, subj, outcome, flags, tests = EXPECT[mail_id]
        if mail_id == "b3-05":
            file_name, msg_id = B305_FILE, B305_ID.strip("<>")
        else:
            file_name, msg_id = names[mail_id], mails[mail_id].message_id_bare
        rows.append({"id": mail_id, "batch": mail_id[1], "file": file_name, "message_id": msg_id,
                     "kind": kind, "group": group, "area": area, "sub_area": sub,
                     "subject": subj, "proposed_outcome": outcome, "flags": flags,
                     "tests": tests})
    return rows


def csv_bytes(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")

# ======================================================================= fixtures


def build_fixtures(tmp):
    """tools/fixtures/sample.eml, sample.docx, EXPECTED.txt as {relative path: bytes}."""
    tmp.mkdir(parents=True, exist_ok=True)
    docx_marker = legal_docs.build_fixture_docx(tmp / "sample.docx")
    attachment = legal_docs.build_fixture_attachment(tmp / "fixture.docx")
    sample = Mail(
        "fixture-eml", local(UK, 2026, 10, 1, 9, 0), TOM, [("", "legal@kestrel-eng.co.uk")],
        "Fixture: sample email", """
This is the fixture email that bash tools/tooling-setup uses to check the email tools on this machine.

It carries one attachment, fixture.docx.

Tom Hale
Kestrel Engineering Ltd""", attachments=[("fixture.docx", attachment, DOCX)])
    eml = sample.to_bytes()
    assert sample.message_id == "<fixture-eml.202610010900@kestrel-eng.co.uk>"
    expected = "\n".join([
        "sample_eml_sha256=" + hashlib.sha256(eml).hexdigest(),
        "sample_eml_message_id=fixture-eml.202610010900@kestrel-eng.co.uk",
        "sample_eml_attachment=fixture.docx",
        "sample_msg_message_id=fixture.202610010900@kestrel-eng.de",
        "sample_docx_marker=FIXTURE-INSERTED-TEXT",
    ]) + "\n"
    return {"tools/fixtures/sample.eml": eml, "tools/fixtures/sample.docx": docx_marker,
            "tools/fixtures/EXPECTED.txt": expected.encode("ascii")}

# ======================================================================= checks


def self_check(outputs, mails, names, att):
    """Parse every email back and check the spec G rules."""
    parser = BytesParser(policy=email_policy.default)
    for mail_id, mail in mails.items():
        path = "demo/batches/%d/%s" % (mail.batch, names[mail_id])
        data = outputs[path]
        msg = parser.parsebytes(data)
        assert msg["Message-ID"] == mail.message_id, (mail_id, msg["Message-ID"])
        assert msg["Date"].datetime.utcoffset() == mail.when.utcoffset(), mail_id
        assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b""), mail_id
        if b"{{REF:" in data:
            assert data.isascii(), mail_id
    # b1-04 and b1-05 carry byte-identical Acme_MSA_v1.docx
    def payload(mail_id, name):
        msg = parser.parsebytes(outputs["demo/batches/1/%s" % names[mail_id]])
        for part in msg.iter_attachments():
            if part.get_filename() == name:
                return part.get_payload(decode=True)
        raise AssertionError((mail_id, name))
    assert payload("b1-04", "Acme_MSA_v1.docx") == payload("b1-05", "Acme_MSA_v1.docx") \
        == att["Acme_MSA_v1.docx"]
    # offsets around the clock change on 25 October 2026, as labelled in the spec G table
    for k, v in mails.items():
        got = int(v.when.utcoffset().total_seconds() // 3600)
        assert got == SPEC_OFFSETS[SPEC_ZONES[k]], (k, got, SPEC_ZONES[k])
    check_questionnaire_map()


SPEC_OFFSETS = {"BST": 1, "GMT": 0, "CEST": 2, "CET": 1}
SPEC_ZONES = {
    "b1-01": "BST", "b1-02": "BST", "b1-03": "CEST", "b1-04": "CEST", "b1-05": "BST",
    "b1-06": "BST", "b1-07": "BST", "b1-08": "BST", "b1-09": "CEST", "b1-10": "BST",
    "b1-11": "BST", "b1-12": "BST",
    "b2-01": "CEST", "b2-02": "CEST", "b2-03": "BST", "b2-04": "BST", "b2-05": "BST",
    "b2-06": "CEST", "b2-07": "BST", "b2-08": "BST", "b2-09": "BST",
    "b3-01": "GMT", "b3-02": "CET", "b3-03": "CET", "b3-04": "GMT", "b3-06": "GMT",
    "b3-07": "GMT", "b3-08": "GMT",
}

# ======================================================================= main


def build_all(work):
    """Everything this builder writes, as {path relative to ROOT: bytes}."""
    att = build_attachments(work / "out")
    mails = build_mails(att)
    names = batch_names(mails)
    outputs = {}
    for mail_id, mail in sorted(mails.items()):
        outputs["demo/batches/%d/%s" % (mail.batch, names[mail_id])] = mail.to_bytes()
    outputs["demo/expected.csv"] = csv_bytes(expected_rows(mails, names))
    sa = work / STANDARD_ANSWERS_FILE
    outputs["demo/knowledge/standard-answers/" + STANDARD_ANSWERS_FILE] = \
        legal_docs.build_past_questionnaire(sa, PAST_QUESTIONNAIRE)
    outputs.update(build_fixtures(work / "fixtures"))
    for name, data in att.items():
        outputs["demo/build/mail/out/" + name] = data
    self_check(outputs, mails, names, att)
    return outputs, mails, names


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the demo mail corpus.")
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and compare with the files on disk")
    args = ap.parse_args(argv)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        outputs, mails, names = build_all(Path(tmp))
    if args.check:
        bad = 0
        for rel, data in sorted(outputs.items()):
            p = ROOT / rel
            if not p.exists() or p.read_bytes() != data:
                print("differs: " + rel)
                bad += 1
        for b in (1, 2, 3):
            for p in sorted((ROOT / ("demo/batches/%d" % b)).glob("*.eml")):
                rel = p.relative_to(ROOT).as_posix()
                if rel not in outputs:
                    print("extra: " + rel)
                    bad += 1
        print("check: %d files compared, %d differ" % (len(outputs), bad))
        return 1 if bad else 0
    for b in (1, 2, 3):
        d = ROOT / ("demo/batches/%d" % b)
        d.mkdir(parents=True, exist_ok=True)
        for p in d.glob("*.eml"):
            p.unlink()
    out_dir = ROOT / "demo/build/mail/out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    for rel, data in sorted(outputs.items()):
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    n_eml = sum(1 for r in outputs if r.startswith("demo/batches/"))
    print("wrote %d emails, demo/expected.csv (%d rows), the standard answers, the fixtures and "
          "%d attachments in demo/build/mail/out/" % (n_eml, len(EXPECT),
                                                      sum(1 for r in outputs if "/out/" in r)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
