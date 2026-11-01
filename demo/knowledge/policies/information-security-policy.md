---
type: policy
name: Information Security Policy
aliases: IS-POL-01, ISMS policy, infosec policy, security policy
owner: IT security
source: Kestrel ISMS document IS-POL-01 version 5.0, approved by the Board of Kestrel Engineering Ltd on 2025-12-09
origin: document
valid_from: 2026-01-01
valid_until:
last_confirmed: 2026-10-09
confirmed_by: Alex Morgan
links:
  - applies_to: knowledge/entities/entity-list.md
  - owned_by: knowledge/people/people-and-roles.md
  - answers_reused_in: knowledge/standard-answers/
---
# Information Security Policy (IS-POL-01, version 5.0)

## Summary

The group's top-level information security policy. It applies to Kestrel Engineering Ltd and Kestrel Pumpen GmbH, all staff and contractors, corporate IT, the factory network and the remote condition monitoring platform that connects gateways at customer sites. It sets who is responsible, what must be protected and how: certification, risk assessment, access control, encryption, patching, testing, incident notification, suppliers and business continuity. Detailed rules are in the standards it names. The Head of IT Security owns it; the Board approves it every year. Version 5.0 took effect on 1 January 2026 and adds annual independent penetration testing.

## Key facts

- Owner: Head of IT Security, who reports to the Chief Financial Officer and reports to the Board every quarter (s 3.2).
- Approved by the Board on 9 December 2025; in force from 1 January 2026; reviewed at least once a year (s 16).
- ISO/IEC 27001:2022 certification for the Sheffield site, covering design, manufacture and remote condition monitoring, corporate IT and the monitoring platform; Kestrel Pumpen GmbH follows the policy but is outside the certificate scope (s 4.1, s 4.2).
- Cyber Essentials Plus renewed every year (s 4.3).
- Multi-factor authentication for all remote access, email, cloud services and administrator accounts (s 8.3).
- TLS 1.2 or higher in transit; AES-256 at rest, including backups (s 9.1).
- Critical patches within 14 days, or 48 hours when actively exploited (s 9.3).
- Vulnerability scans: internal monthly, external weekly (s 9.4).
- Independent penetration test of internet-facing systems and the monitoring platform at least every 12 months and after major changes; critical and high findings fixed within 30 days (s 9.6, new in version 5.0).
- Customers told of an incident affecting their data or systems without undue delay and within 24 hours of confirmation (s 12.3).
- Customer data stored and processed only in the UK and the EEA (s 14.1).
- Recovery time objective for the monitoring platform: 8 hours (s 13.2).

## Policy

### 1. Purpose

1.1 This policy protects the confidentiality, integrity and availability of information held by the Kestrel group and by our customers, and supports the commitments we make in customer contracts.

1.2 It sets the principles. The standards and procedures named in it set the detail. Where a customer contract sets a stricter rule, the contract applies to that customer's information.

### 2. Scope

2.1 This policy applies to Kestrel Engineering Ltd and Kestrel Pumpen GmbH, and to every employee, contractor and temporary worker who uses group information or systems.

2.2 It covers corporate IT, the factory operational technology (OT) network, the remote condition monitoring platform, the monitoring gateways installed at customer sites, and information held on paper.

### 3. Roles and responsibilities

3.1 The Board is accountable for information security and approves this policy every year.

3.2 The Head of IT Security owns this policy and the information security management system (ISMS). The Head of IT Security reports to the Chief Financial Officer and presents a security report to the Board every quarter.

3.3 The Information Security Committee (Chief Financial Officer as chair, Head of IT Security, Operations Director, Senior Legal Counsel, Head of People) meets every quarter. It reviews risks, incidents, exceptions and audit findings.

3.4 System owners and information asset owners approve access to their systems and information and take part in access reviews.

3.5 Every member of staff protects the information they handle and reports suspected incidents at once to the IT service desk.

### 4. Certification and external assurance

4.1 Kestrel maintains certification of its ISMS to ISO/IEC 27001:2022, with annual surveillance audits by an accredited certification body. The scope is the design, manufacture and remote condition monitoring of industrial pumps at the Sheffield site, including corporate IT and the monitoring platform.

4.2 Kestrel Pumpen GmbH follows this policy and the standards under it, but its Dortmund site is outside the scope of the ISO/IEC 27001 certificate.

4.3 Kestrel Engineering Ltd renews its Cyber Essentials Plus certification every year.

4.4 IT Security keeps the current certificates and the Statement of Applicability. The Statement of Applicability is shared with customers only under a confidentiality agreement.

### 5. Risk management

5.1 IT Security keeps the information security risk register. A full risk assessment is carried out every year and whenever there is a significant change to systems, sites or services.

5.2 The IT leadership team reviews the register every month. Risks rated high are reported to the Information Security Committee, and risks above the group's risk appetite are accepted only by the Chief Financial Officer.

### 6. People

6.1 Before they start, all staff are screened in line with the Recruitment and Screening Procedure: identity, right to work, three years' employment history and two references. Staff with privileged IT access or access to customer systems also have a basic criminal record check.

6.2 Employment contracts and contractor agreements contain confidentiality obligations that continue after the engagement ends.

6.3 All staff and contractors complete security awareness training when they join and every year after that. IT Security runs simulated phishing exercises every quarter.

### 7. Information classification and handling

7.1 Information is classified as Public, Internal, Confidential or Restricted, and handled under the Information Classification Standard.

7.2 Customer information is Confidential as a minimum. Customer network details, credentials and security reports are Restricted.

### 8. Access control

8.1 Access is role-based and granted on a least-privilege basis. Every request goes through the IT service desk and is approved by the line manager and the system owner before it is granted (Access Control Policy).

8.2 Administrators use separate named administrator accounts, which are never shared. Administrator rights are granted just in time through the privileged access management tool, and privileged sessions are logged and reviewed (Privileged Access Procedure).

8.3 Multi-factor authentication is enforced for all remote access, email and cloud services, and for all administrator accounts.

8.4 Passwords follow the Password Standard: at least 14 characters, checked against known breached passwords, no forced periodic change unless compromise is suspected, and lockout after 10 failed attempts.

8.5 Access rights are reviewed every quarter for critical systems and every six months for other systems. IT Security reviews privileged access every month.

8.6 Leavers' accounts are disabled at the end of their last working day, and within 4 hours of a dismissal. The leaver process starts automatically from the HR system.

### 9. Technical security

9.1 Encryption follows the Cryptography Standard: TLS 1.2 or higher for all external connections, with TLS 1.3 preferred; AES-256 for data at rest, including backups; full-disk encryption on laptops. Keys are held in a managed key vault backed by hardware security modules and rotated at least once a year.

9.2 Endpoint detection and response software runs on all servers and end-user devices. A managed security service provider monitors alerts 24 hours a day and escalates to IT Security.

9.3 Security patches are applied in a monthly cycle. Critical patches are applied within 14 days, or within 48 hours where a vulnerability is being actively exploited (Patch Management Procedure).

9.4 Authenticated internal vulnerability scans run every month and external scans of internet-facing systems run every week. Findings are fixed within the patching timescales.

9.5 Logs from servers, firewalls, cloud services and endpoints are collected in a central security information and event management system, monitored 24 hours a day by the managed security service provider, and kept for 12 months.

9.6 An independent penetration test of Kestrel's internet-facing systems and of the remote condition monitoring platform is carried out at least once every 12 months, and after any major change to either. The tester must be accredited by a recognised penetration testing accreditation scheme. Findings rated critical or high are fixed within 30 days and retested. IT Security keeps the reports and may give customers a summary letter from the tester under a confidentiality agreement.

9.7 Networks are protected by next-generation firewalls at the perimeter and between zones. The network is segmented into office, server, factory (OT) and guest zones, and the factory OT network is isolated from the office network.

9.8 USB storage devices are blocked by default. Exceptions need IT Security approval and use encrypted company devices.

9.9 Backups are taken daily (incremental) and weekly (full), encrypted, with a copy held off-site and an immutable copy in the cloud. Restores are tested every quarter.

9.10 Changes to production systems go through the change management process and the Change Advisory Board. Development, test and production environments are kept separate, and live customer data is used in test only if it has been anonymised.

### 10. Remote condition monitoring and customer sites

10.1 Monitoring gateways at customer sites make outbound-only encrypted connections (TLS 1.2 or higher) to Kestrel's monitoring platform. No inbound ports are opened on a customer's network.

10.2 Kestrel engineers connect to a customer's network only through the customer's own remote access service, with named accounts and multi-factor authentication, and only where the customer has agreed to it.

10.3 Gateways run a hardened operating system image with unused services disabled, secure boot and a unique device certificate.

10.4 Gateway firmware updates are signed, tested and deployed remotely at least every quarter (Gateway Hardening Standard).

### 11. Suppliers and subcontractors

11.1 Suppliers who will have access to Kestrel or customer information complete a security assessment before the contract and every two years after that (Supplier Security Procedure).

11.2 Supplier contracts include security and confidentiality obligations and a right to audit. Subcontractors that store or process customer data are listed in the subprocessor list, which IT Security keeps with Legal.

### 12. Security incidents

12.1 The Security Incident Response Plan sets out roles, severity levels and escalation. It is tested every year with a tabletop exercise.

12.2 Every suspected incident is reported to the IT service desk at once. IT Security leads the response. Legal decides on any notification to a regulator or to affected individuals.

12.3 A customer is told without undue delay, and in any case within 24 hours of Kestrel confirming an incident affecting that customer's data or systems, with updates as the investigation progresses. A shorter period agreed in a customer contract applies to that customer.

### 13. Business continuity

13.1 The business continuity plan covers manufacturing, IT and the remote condition monitoring service.

13.2 The recovery time objective for the monitoring platform is 8 hours. The plans are tested every year.

### 14. Data location, retention and data protection

14.1 Customer data is stored and processed only in the UK and the European Economic Area.

14.2 Customer data is returned or deleted within 30 days of the end of a contract unless the contract says otherwise. Storage media are wiped to a recognised standard (NIST SP 800-88) or physically destroyed by a certified contractor (Data Retention and Disposal Procedure).

14.3 Kestrel Engineering Ltd complies with the UK GDPR and the Data Protection Act 2018, and Kestrel Pumpen GmbH with the EU GDPR. The Legal team is responsible for data protection, supported by the Head of IT Security (Data Protection Policy).

### 15. Exceptions and breaches of this policy

15.1 An exception to this policy must be requested in writing and approved by the Head of IT Security. An exception that leaves a high risk open must also be accepted by the Chief Financial Officer.

15.2 Exceptions are recorded in the exceptions register and reviewed every six months.

15.3 A breach of this policy may lead to disciplinary action, or to the end of a contractor's engagement.

### 16. Review, approval and history

16.1 The Head of IT Security reviews this policy at least once a year, and after any major incident or change. The Board approves each version.

| Version | Approved by the Board | In force from | Main changes |
|---|---|---|---|
| 5.0 | 9 December 2025 | 1 January 2026 | Adds annual independent penetration testing with a 30-day fix target for critical and high findings (s 9.6); moves the gateway update cycle into the policy (s 10.4); adds the six-monthly review of exceptions (s 15.2) |
| 4.0 | 10 December 2024 | 1 January 2025 | Adds the factory OT network to the scope; sets the 24-hour customer notification (s 12.3) |
