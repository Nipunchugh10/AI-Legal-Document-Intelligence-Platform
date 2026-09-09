"""
scripts/seed_demo.py
--------------------
Seeds the AI Legal Document Intelligence Platform with realistic demo evaluation data:
1. Demo user accounts:
   - Primary: demo@legalai.com (Password: DemoPassword2026!)
   - Alternative: lawyer@example.com (Password: SecurePassword123!)
   Both accounts have 2FA disabled by default so reviewers/recruiters can log in immediately.
2. 5 Realistic Legal Contracts across key commercial domains:
   - 1. Mutual Non-Disclosure Agreement (NDA) - Apex Innovations & Nexus Solutions
   - 2. Master Cloud Services Agreement (SaaS MSA) - CloudSphere & Enterprise Global Retail
   - 3. Executive Employment Agreement (CTO) - Vanguard Media & Dr. Rajesh Sharma
   - 4. Commercial Indenture of Lease - Horizon Realty Trust & Omni Retail Ventures
   - 5. Independent Contractor Consulting Agreement - Apex AI Labs & Priya Verma
3. Complete Multi-Agent Analysis Findings for each contract:
   - Raw text extracted
   - Parsing agent metadata (parties, date, jurisdiction, document type)
   - Universal 9-clause checklist evaluation
   - 3-tier traffic light risk assessment (red, yellow, green flags)
   - 8-domain statutory compliance findings
   - Comprehensive executive summaries
4. Interactive Q&A Conversations with verbatim clause citations
5. Full Audit Log activity history for the timeline and analytics dashboard

Usage:
  python scripts/seed_demo.py
  # or from backend/:
  cd backend && python ../scripts/seed_demo.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend modules are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
settings = get_settings()
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Analysis
from app.models.conversation import Conversation, ConversationMessage
from app.models.audit_log import AuditLog
from app.core.audit_events import AuditEventType

# Sample contract texts
CONTRACT_TEXTS = {
    "nda": """MUTUAL CONFIDENTIALITY AND NON-DISCLOSURE AGREEMENT

THIS NON-DISCLOSURE AGREEMENT ("Agreement") is made and entered into as of November 1, 2026 ("Effective Date"),
by and between Apex Innovations Inc., a Delaware corporation having its principal office at 500 Silicon Ave, Wilmington, DE ("Disclosing Party"),
and Nexus Solutions Ltd., a company organized under the laws of the United Kingdom, having its office at 100 London Wall, London ("Receiving Party").
The Disclosing Party and Receiving Party are collectively referred to as the "Parties" or individually as a "Party."

1. PURPOSE AND DEFINITION OF CONFIDENTIAL INFORMATION
The Parties wish to explore a potential strategic commercial partnership in AI software systems ("Purpose"). 
"Confidential Information" means all non-public, proprietary, or confidential information disclosed by one Party to the other,
whether orally or in writing, including without limitation source code, algorithms, customer lists, business strategies, and product roadmaps.

2. EXCLUSIONS FROM CONFIDENTIALITY
Confidential Information shall NOT include information that:
(a) is or becomes publicly known through no breach of this Agreement by Receiving Party;
(b) was already in Receiving Party's rightful possession prior to disclosure without confidentiality obligations;
(c) is independently developed by Receiving Party without reference to or reliance upon Disclosing Party's Confidential Information; or
(d) is rightfully received from a third party without duty of non-disclosure.

3. COMPELLED DISCLOSURE
If Receiving Party is compelled by applicable law, regulation, or order of a court of competent jurisdiction to disclose any Confidential Information,
it shall provide prompt written notice to Disclosing Party prior to such disclosure to enable Disclosing Party to seek a protective order.

4. NON-DISCLOSURE AND STANDARD OF CARE
Receiving Party agrees to hold all Confidential Information in strict confidence, exercising at least the same degree of care as it uses for its own confidential assets,
but no less than a reasonable degree of care. Receiving Party shall not disclose Confidential Information to any third party except to its directors, officers,
and employees who need to know such information for the Purpose.

5. DURATION AND TERMINATION
This Agreement and the obligations herein shall remain in effect for a period of three (3) years from the Effective Date;
provided, however, that with respect to any trade secrets disclosed hereunder, the obligations of confidentiality shall survive perpetually.

6. RETURN OF MATERIALS
Promptly upon written request by Disclosing Party or upon termination of this Agreement, Receiving Party shall destroy or return all documents, notes,
and copies containing Confidential Information.

7. GOVERNING LAW AND JURISDICTION
This Agreement shall be governed by and construed in accordance with the substantive laws of the State of Delaware, USA,
without regard to conflicts of law principles. Any dispute arising out of or in connection with this Agreement shall be submitted to the exclusive jurisdiction of the state and federal courts located in New Castle County, Delaware.
""",

    "saas_msa": """MASTER CLOUD SERVICES AGREEMENT (MSA)

This Cloud Services Master Agreement ("Agreement") is entered into as of October 15, 2026 ("Effective Date")
between CloudSphere Technologies Corp., a California corporation ("Provider"), and Enterprise Global Retail LLC, a Texas limited liability company ("Customer").

Section 1. Cloud Software Services.
Provider grants Customer a non-exclusive, non-transferable subscription right to access and use Provider's AI Document Intelligence Cloud Platform
during the Term solely for Customer's internal business operations.

Section 2. Fees, Invoicing and Payment Terms.
Customer shall pay all subscription fees specified in Order Form 1 within thirty (30) days of receipt of invoice ("net-30").
Overdue balances shall accrue interest at the rate of 1.5% per month or the maximum legal rate, whichever is lower.
Fees are non-refundable except as expressly provided herein.

Section 3. Term, Auto-Renewal and Cancellation.
This Agreement shall commence on the Effective Date for an initial term of twelve (12) months ("Initial Term").
Thereafter, this Agreement shall automatically renew for successive twelve (12) month periods (each a "Renewal Term"),
unless either party provides written notice of non-renewal at least thirty (30) days prior to the expiration of the then-current term.
Provider reserves the right to increase annual subscription fees by up to 5% upon sixty (60) days prior written notice before renewal.

Section 4. Termination and Default.
Either party may terminate this Agreement immediately upon written notice if the other party breaches any material term and fails to cure
such breach within thirty (30) days of receiving written notice. Customer may terminate this Agreement for convenience upon sixty (60) days prior written notice,
subject to payment of all accrued fees up to the effective termination date.

Section 5. Limitation of Liability.
IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL, OR PUNITIVE DAMAGES,
INCLUDING LOSS OF PROFITS, DATA, OR BUSINESS INTERRUPTION, ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT.
EACH PARTY'S TOTAL AGGREGATE LIABILITY UNDER OR RELATING TO THIS AGREEMENT SHALL BE LIMITED TO THE TOTAL FEES PAID OR PAYABLE
BY CUSTOMER TO PROVIDER IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO LIABILITY.

Section 6. Data Protection and Security.
Provider shall implement and maintain commercially reasonable administrative, physical, and technical safeguards to protect Customer Data against unauthorized access.
Customer retains full ownership of all data uploaded to the Service.

Section 7. Governing Law and Arbitration.
This Agreement will be interpreted in accordance with the laws of the State of California.
Any dispute arising out of this Agreement shall be resolved through binding arbitration administered by JAMS in San Francisco, California.
""",

    "employment": """EXECUTIVE EMPLOYMENT AGREEMENT

THIS EXECUTIVE EMPLOYMENT AGREEMENT ("Agreement") is made effective as of January 1, 2027 ("Effective Date"),
by and between Vanguard Media Technologies Pvt. Ltd., a company incorporated under the Companies Act, 2013, with registered office at Connaught Place, New Delhi ("Company"),
and Dr. Rajesh Sharma, an individual residing at Vasant Vihar, New Delhi ("Executive").

1. POSITION AND DUTIES
The Company agrees to employ Executive as Chief Technology Officer (CTO). Executive shall report directly to the Chief Executive Officer and Board of Directors.
Executive shall devote full business time and best efforts to the performance of duties.

2. COMPENSATION AND BONUS
Executive shall receive an annual base salary of INR 75,00,000 (Indian Rupees Seventy-Five Lakhs), payable monthly in arrears subject to applicable tax deductions (TDS).
Executive shall be eligible for an annual performance bonus of up to 30% of base salary based on KPIs established by the Board.

3. INTELLECTUAL PROPERTY ASSIGNMENT
Executive agrees that all inventions, designs, software, proprietary discoveries, and work product developed during employment shall belong exclusively to the Company.
Executive hereby assigns all rights, title, and interest in such creations to the Company. (Note: Territorial scope and duration are not specified in this clause).

4. POST-TERMINATION NON-COMPETE COVENANT
Executive agrees that for a period of two (2) years following the termination of employment for any reason,
Executive shall not, directly or indirectly, whether as an employee, consultant, officer, director, partner, or shareholder,
engage in, work for, or provide advisory services to any competing business or media technology enterprise in the territory of India.

5. TERMINATION AND NOTICE PERIOD
Either party may terminate this Agreement by providing ninety (90) days prior written notice to the other party.
The Company may terminate Executive immediately for cause in cases of fraud, gross misconduct, or conviction of a felony without notice.

6. GOVERNING LAW AND FORUM
This Agreement shall be governed by, and construed in accordance with, the laws of the Republic of India.
The competent civil courts situated in New Delhi, India shall have exclusive jurisdiction over all disputes arising from this Agreement.
""",

    "lease": """COMMERCIAL INDENTURE OF LEASE

THIS INDENTURE OF LEASE is executed on August 1, 2026 ("Effective Date"),
by and between Horizon Commercial Realty Trust, having its corporate office at Prestige Towers, MG Road, Bangalore ("Lessor"),
and Omni Retail Ventures Ltd., having its registered office at Indiranagar, Bangalore ("Lessee").

WHEREAS Lessor is the absolute lawful owner of the commercial property consisting of 5,000 square feet on the 3rd Floor ("Demised Premises").
AND WHEREAS Lessee desires to lease the Demised Premises for commercial retail and corporate office operations.

NOW THIS AGREEMENT WITNESSETH AS FOLLOWS:

1. LEASE TERM AND LOCK-IN PERIOD
The lease shall be for a total period of five (5) years commencing on August 1, 2026.
There shall be a strict mandatory lock-in period of thirty-six (36) months from the commencement date.
If the Lessee vacates or terminates the lease before the expiry of the lock-in period, the Lessee shall be liable to pay
the entire rental for the remainder of the 36-month lock-in period as liquidated damages.

2. MONTHLY RENT AND ESCALATION
The monthly rent shall be INR 3,50,000 (Indian Rupees Three Lakhs Fifty Thousand), payable on or before the 5th day of every calendar month.
The rent shall automatically escalate by 15% every three (3) years from the commencement date.

3. SECURITY DEPOSIT
Lessee has deposited an interest-free refundable security deposit of INR 21,00,000 (equivalent to six months rent) with Lessor.
The security deposit shall be refunded within thirty (30) days of vacating the Demised Premises after adjusting for unpaid utility dues.

4. MAINTENANCE AND UTILITIES
Lessee shall pay monthly Common Area Maintenance (CAM) charges of INR 40,000 plus applicable GST directly to the Building Association.

5. DISPUTE RESOLUTION AND ARBITRATION
All disputes, controversies, or claims arising out of this Lease shall be referred to a Sole Arbitrator appointed exclusively by the Lessor.
The seat of arbitration shall be Bangalore, Karnataka, and the arbitration proceedings shall be conducted under the Arbitration and Conciliation Act, 1996.
The courts in Bangalore, Karnataka, India shall have supervisory jurisdiction.
""",

    "freelance": """INDEPENDENT CONTRACTOR CONSULTING AGREEMENT

This Consulting Agreement ("Agreement") is entered into as of September 1, 2026 ("Effective Date"),
by and between Apex AI Labs Inc., a company registered in Delaware, USA ("Client"),
and Priya Verma, an independent professional consultant residing in Mumbai, Maharashtra, India ("Consultant").

1. SERVICES AND DELIVERABLES
Consultant shall develop and optimize deep learning algorithms for legal document extraction ("Deliverables")
as outlined in Statement of Work (SOW) #1 attached hereto.

2. COMPENSATION AND MILESTONE PAYMENT
Client shall pay Consultant a total fee of $12,000 USD, payable in milestones upon written acceptance of deliverables:
- Milestone 1: $4,000 upon system architecture approval;
- Milestone 2: $4,000 upon model training and benchmark delivery;
- Milestone 3: $4,000 upon production deployment.
Invoices shall be paid within fifteen (15) days of approval. Overdue invoices shall bear interest at 2.5% per month.

3. UNILATERAL TERMINATION
Client may terminate this Agreement at any time for convenience with immediate effect upon written email notice.
In the event of such immediate termination, Consultant shall immediately cease work and Client shall not be liable to pay for any work-in-progress that has not been approved in a completed milestone.

4. INDEMNIFICATION BY CONSULTANT
Consultant shall unconditionally defend, indemnify, and hold harmless Client, its affiliates, and officers from and against
any and all liabilities, losses, damages, claims, and expenses (including attorneys' fees) arising out of or related to
Consultant's services, work product, or alleged infringement of third-party intellectual property rights, without any monetary cap.

5. DATA PRIVACY AND PROTECTION
Consultant shall process customer data provided by Client solely for performing the services.
Consultant shall maintain backups. (Note: No Data Protection Officer or 7-15 day grievance redressal mechanism is provided).

6. GOVERNING LAW AND JURISDICTION
This Agreement shall be governed by and construed in accordance with the laws of India.
Any dispute shall be subject to the exclusive jurisdiction of the courts located in Mumbai, Maharashtra, India.
"""
}


def build_contract_data():
    """Builds rich pre-analyzed dataset for all 5 demo contracts."""
    return [
        {
            "key": "nda",
            "filename": "Mutual_Non_Disclosure_Agreement_Apex_Nexus.pdf",
            "doc_type": "Non-Disclosure Agreement (NDA)",
            "parties": ("Apex Innovations Inc.", "Nexus Solutions Ltd."),
            "effective_date": "2026-11-01",
            "jurisdiction": "Delaware, USA",
            "summary": "A bilateral mutual non-disclosure agreement between Apex Innovations and Nexus Solutions to explore strategic AI partnership. 3-year term with perpetual confidentiality for trade secrets, Delaware governing law, and customary exclusions.",
            "clauses": {
                "confidentiality_clauses": {"present": True, "text": "Receiving Party agrees to hold all Confidential Information in strict confidence...", "location": "Section 1 & 4"},
                "termination_clauses": {"present": True, "text": "This Agreement and obligations shall remain in effect for three (3) years...", "location": "Section 5"},
                "governing_law_clauses": {"present": True, "text": "Governed by and construed in accordance with laws of Delaware...", "location": "Section 7"},
                "dispute_resolution_clauses": {"present": True, "text": "Exclusive jurisdiction of state and federal courts in New Castle County, Delaware.", "location": "Section 7"},
                "payment_terms": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
                "liability_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
                "intellectual_property_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
                "renewal_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
                "indemnification_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
            },
            "risks": [
                {
                    "category": "Confidentiality",
                    "severity": "LOW",
                    "issue": "Trade secret confidentiality obligations survive perpetually.",
                    "recommendation": "Standard commercial practice for trade secrets; ensure cataloging of shared technical IP.",
                    "citation": "Section 5 (Duration and Termination)"
                },
                {
                    "category": "Compliance",
                    "severity": "LOW",
                    "issue": "Written notice required prior to legally compelled disclosures.",
                    "recommendation": "Protective term ensuring disclosing party can seek protective orders.",
                    "citation": "Section 3 (Compelled Disclosure)"
                }
            ],
            "compliance": [
                {
                    "domain": "corporate_signatory_authority",
                    "severity": "LOW",
                    "issue": "Corporate form validly specified for Delaware corporation and UK entity.",
                    "finding": "Compliant with corporate signatory conventions.",
                    "recommendation": "Verify officer signatory authority prior to execution."
                },
                {
                    "domain": "arbitration_dispute_rules",
                    "severity": "LOW",
                    "issue": "Court venue specified without mandatory arbitration clause.",
                    "finding": "Standard Delaware Chancery / Federal court submission.",
                    "recommendation": "Acceptable for bilateral confidentiality protection."
                }
            ]
        },
        {
            "key": "saas_msa",
            "filename": "Master_Cloud_Services_Agreement_CloudSphere.pdf",
            "doc_type": "Master Services Agreement (MSA)",
            "parties": ("CloudSphere Technologies Corp.", "Enterprise Global Retail LLC"),
            "effective_date": "2026-10-15",
            "jurisdiction": "California, USA",
            "summary": "Enterprise cloud SaaS subscription agreement for AI Document Intelligence. 12-month auto-renewing term, net-30 payments, 12-month trailing fee liability cap, California governing law with JAMS arbitration.",
            "clauses": {
                "payment_terms": {"present": True, "text": "Customer shall pay all subscription fees within thirty (30) days of invoice ('net-30')...", "location": "Section 2"},
                "termination_clauses": {"present": True, "text": "Either party may terminate upon 30-day notice for material breach. Customer may terminate for convenience upon 60 days notice.", "location": "Section 4"},
                "liability_clauses": {"present": True, "text": "Each party's total aggregate liability is limited to fees paid in preceding 12 months.", "location": "Section 5"},
                "renewal_clauses": {"present": True, "text": "Automatically renews for successive 12-month periods unless notice of non-renewal given 30 days prior.", "location": "Section 3"},
                "dispute_resolution_clauses": {"present": True, "text": "Binding arbitration administered by JAMS in San Francisco, California.", "location": "Section 7"},
                "governing_law_clauses": {"present": True, "text": "Interpreted in accordance with laws of State of California.", "location": "Section 7"},
                "confidentiality_clauses": {"present": True, "text": "Customer retains full ownership of data; safeguards required.", "location": "Section 6"},
                "intellectual_property_clauses": {"present": True, "text": "Non-exclusive subscription right to use Platform.", "location": "Section 1 & 6"},
                "indemnification_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
            },
            "risks": [
                {
                    "category": "Pricing Exposure",
                    "severity": "MEDIUM",
                    "issue": "Provider may increase subscription fees by up to 5% annually upon 60 days notice.",
                    "recommendation": "Cap annual price increases at CPI or 3%, and provide right to terminate without penalty if increase exceeds cap.",
                    "citation": "Section 3 (Term, Auto-Renewal and Cancellation)"
                },
                {
                    "category": "Limitation of Liability",
                    "severity": "MEDIUM",
                    "issue": "Aggregate liability capped at 12-month trailing fees with waiver of data loss damages.",
                    "recommendation": "Carve out data security breaches and confidentiality violations from the liability cap and consequential damage waiver.",
                    "citation": "Section 5 (Limitation of Liability)"
                }
            ],
            "compliance": [
                {
                    "domain": "data_privacy_dpdp_gdpr",
                    "severity": "MEDIUM",
                    "issue": "Lacks specific GDPR/CCPA Data Processing Addendum (DPA) terms.",
                    "finding": "General data protection stated but detailed subprocessor disclosure is missing.",
                    "recommendation": "Attach formal DPA governing cross-border transfers and security breach notifications."
                },
                {
                    "domain": "consumer_fairness",
                    "severity": "LOW",
                    "issue": "Auto-renewal mechanism requires 30 days non-renewal notice.",
                    "finding": "Compliant with B2B commercial contracting standards.",
                    "recommendation": "Configure automated calendar reminders 45 days before renewal."
                }
            ]
        },
        {
            "key": "employment",
            "filename": "Executive_Employment_Agreement_Dr_Sharma.pdf",
            "doc_type": "Executive Employment Agreement",
            "parties": ("Vanguard Media Technologies Pvt. Ltd.", "Dr. Rajesh Sharma"),
            "effective_date": "2027-01-01",
            "jurisdiction": "New Delhi, India",
            "summary": "Executive employment agreement engaging Dr. Rajesh Sharma as CTO of Vanguard Media Technologies. Annual compensation of INR 75 Lakhs + 30% bonus, 90-day notice period, New Delhi jurisdiction.",
            "clauses": {
                "payment_terms": {"present": True, "text": "Annual base salary of INR 75,00,000 payable monthly in arrears with up to 30% bonus...", "location": "Section 2"},
                "termination_clauses": {"present": True, "text": "Either party may terminate with 90 days written notice. Immediate for cause.", "location": "Section 5"},
                "intellectual_property_clauses": {"present": True, "text": "Inventions and software developed during employment belong exclusively to Company.", "location": "Section 3"},
                "governing_law_clauses": {"present": True, "text": "Governed by laws of the Republic of India.", "location": "Section 6"},
                "dispute_resolution_clauses": {"present": True, "text": "Competent civil courts in New Delhi, India have exclusive jurisdiction.", "location": "Section 6"},
                "confidentiality_clauses": {"present": True, "text": "Proprietary work product and discoveries assigned to Company.", "location": "Section 3"},
                "renewal_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
                "liability_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
                "indemnification_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
            },
            "risks": [
                {
                    "category": "Restraint of Trade",
                    "severity": "HIGH",
                    "issue": "Two-year post-termination non-compete covenant covering India is void under Indian law.",
                    "recommendation": "Under Section 27 of the Indian Contract Act, 1872, post-employment non-competes are void ab initio. Replace with enforceable non-solicitation of clients/employees.",
                    "citation": "Section 4 (Post-Termination Non-Compete Covenant)"
                },
                {
                    "category": "Intellectual Property",
                    "severity": "MEDIUM",
                    "issue": "IP assignment clause does not specify territorial scope or duration under Indian Copyright Act Section 19(5).",
                    "recommendation": "Explicitly define assignment as worldwide and perpetual to prevent statutory 5-year reversion to author.",
                    "citation": "Section 3 (Intellectual Property Assignment)"
                }
            ],
            "compliance": [
                {
                    "domain": "non_compete_enforceability",
                    "severity": "HIGH",
                    "issue": "Post-termination non-compete covenant is completely void under Indian law.",
                    "finding": "Violates Section 27 of Indian Contract Act, 1872 (Percept D'Mark v. Zaheer Khan).",
                    "recommendation": "Remove clause or reframe as narrow confidentiality and non-solicitation obligation."
                },
                {
                    "domain": "employment_standards",
                    "severity": "LOW",
                    "issue": "Notice period of 90 days meets executive market norms.",
                    "finding": "Compliant with Delhi Shops and Establishments Act standards.",
                    "recommendation": "Include payment in lieu of notice option for company and employee."
                }
            ]
        },
        {
            "key": "lease",
            "filename": "Commercial_Indenture_of_Lease_Horizon_Omni.pdf",
            "doc_type": "Commercial Lease Agreement",
            "parties": ("Horizon Commercial Realty Trust", "Omni Retail Ventures Ltd."),
            "effective_date": "2026-08-01",
            "jurisdiction": "Bangalore, Karnataka, India",
            "summary": "5-year commercial lease for 5,000 sq.ft retail space in Bangalore. Monthly rent INR 3.5 Lakhs, 6-month security deposit, 36-month lock-in period with high liquidated damages exposure.",
            "clauses": {
                "payment_terms": {"present": True, "text": "Monthly rent of INR 3,50,000 payable on 5th of every month. 15% escalation every 3 years.", "location": "Clause 2"},
                "termination_clauses": {"present": True, "text": "36-month mandatory lock-in period. Liquidated damages equal to entire remaining rent.", "location": "Clause 1"},
                "renewal_clauses": {"present": True, "text": "5-year total term commencing August 1, 2026.", "location": "Clause 1"},
                "dispute_resolution_clauses": {"present": True, "text": "Referred to Sole Arbitrator appointed exclusively by Lessor. Bangalore seat.", "location": "Clause 5"},
                "governing_law_clauses": {"present": True, "text": "Arbitration and Conciliation Act, 1996; supervisory courts in Bangalore.", "location": "Clause 5"},
                "liability_clauses": {"present": True, "text": "Entire rental for remainder of 36-month lock-in payable upon early exit.", "location": "Clause 1"},
                "confidentiality_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
                "intellectual_property_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
                "indemnification_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
            },
            "risks": [
                {
                    "category": "Arbitration Enforceability",
                    "severity": "HIGH",
                    "issue": "Sole Arbitrator appointed exclusively by Lessor violates statutory neutrality.",
                    "recommendation": "Under Section 12(5) of Arbitration Act, 1996 and TRF Ltd. Supreme Court precedent, unilateral arbitrator appointments are void. Change to mutual consent.",
                    "citation": "Clause 5 (Dispute Resolution and Arbitration)"
                },
                {
                    "category": "Lock-in Exposure",
                    "severity": "HIGH",
                    "issue": "36-month lock-in with 100% remaining rent as liquidated damages is punitive.",
                    "recommendation": "Under Indian Contract Act Section 74, liquidated damages must be genuine pre-estimate of loss. Negotiate 3-month rental exit cap after 12 months.",
                    "citation": "Clause 1 (Lease Term and Lock-In Period)"
                }
            ],
            "compliance": [
                {
                    "domain": "arbitration_dispute_rules",
                    "severity": "HIGH",
                    "issue": "Unilateral arbitrator nomination is invalid under Section 12(5) of Arbitration Act.",
                    "finding": "In direct violation of 7th Schedule statutory neutrality mandates.",
                    "recommendation": "Amend to require institutional appointment via Bangalore Mediation Centre or mutual agreement."
                },
                {
                    "domain": "commercial_lease_statutes",
                    "severity": "MEDIUM",
                    "issue": "Registration and stamp duty required under Karnataka Stamp Act.",
                    "finding": "Lease exceeding 11 months requires compulsory registration under Section 17 of Registration Act, 1908.",
                    "recommendation": "Ensure agreement is registered with Sub-Registrar to maintain evidentiary admissibility."
                }
            ]
        },
        {
            "key": "freelance",
            "filename": "Independent_Contractor_Consulting_Agreement_Apex_Verma.pdf",
            "doc_type": "Consulting & Services Agreement",
            "parties": ("Apex AI Labs Inc.", "Priya Verma"),
            "effective_date": "2026-09-01",
            "jurisdiction": "Mumbai, Maharashtra, India",
            "summary": "AI engineering consulting contract for $12,000 USD milestone fee. Features heavily client-favored terms including immediate termination for convenience and uncapped consultant indemnification.",
            "clauses": {
                "payment_terms": {"present": True, "text": "$12,000 USD total in 3 milestones ($4k each). Paid within 15 days of approval. 2.5% monthly late interest.", "location": "Section 2"},
                "termination_clauses": {"present": True, "text": "Client may terminate at any time for convenience with immediate email notice with zero WIP liability.", "location": "Section 3"},
                "indemnification_clauses": {"present": True, "text": "Consultant unconditionally indemnifies Client against all claims and third-party IP infringement without cap.", "location": "Section 4"},
                "intellectual_property_clauses": {"present": True, "text": "Deliverables developed for Client outlined in SOW #1.", "location": "Section 1 & 4"},
                "confidentiality_clauses": {"present": True, "text": "Customer data processed solely for services; backups maintained.", "location": "Section 5"},
                "governing_law_clauses": {"present": True, "text": "Governed by and construed in accordance with laws of India.", "location": "Section 6"},
                "dispute_resolution_clauses": {"present": True, "text": "Exclusive jurisdiction of courts located in Mumbai, India.", "location": "Section 6"},
                "liability_clauses": {"present": True, "text": "Uncapped indemnification covering attorneys' fees and IP infringement.", "location": "Section 4"},
                "renewal_clauses": {"present": False, "text": "Not mentioned", "location": "Not mentioned"},
            },
            "risks": [
                {
                    "category": "Uncapped Indemnity",
                    "severity": "HIGH",
                    "issue": "Consultant provides unconditional indemnity without monetary cap.",
                    "recommendation": "Cap indemnity exposure at 1x or 2x total consulting fees received ($12,000–$24,000 USD) and restrict to gross negligence.",
                    "citation": "Section 4 (Indemnification by Consultant)"
                },
                {
                    "category": "Unilateral Termination",
                    "severity": "HIGH",
                    "issue": "Client can terminate immediately without paying for work-in-progress.",
                    "recommendation": "Require minimum 15 days written notice and guarantee payment for pro-rata milestone work performed up to termination.",
                    "citation": "Section 3 (Unilateral Termination)"
                }
            ],
            "compliance": [
                {
                    "domain": "data_privacy_dpdp_gdpr",
                    "severity": "MEDIUM",
                    "issue": "Lacks Data Protection Officer (DPO) and 72-hour breach notice clause under India DPDP Act 2023.",
                    "finding": "Generic data protection reference insufficient for sensitive data fiduciary obligations.",
                    "recommendation": "Incorporate standardized DPDP Act 2023 schedule specifying data erasure on termination."
                },
                {
                    "domain": "consumer_fairness",
                    "severity": "HIGH",
                    "issue": "One-sided forfeiture of work-in-progress is commercially unconscionable.",
                    "finding": "Creates severe financial asymmetry between corporate client and independent contractor.",
                    "recommendation": "Add clause guaranteeing compensation for verified hours spent on active milestones."
                }
            ]
        }
    ]


def seed_demo_data():
    """Main seeding logic."""
    print("=" * 60)
    print("🌱 SEEDING DEMO EVALUATION DATA FOR AI LEGAL PLATFORM")
    print("=" * 60)

    # 1. Ensure all database tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 2. Seed Users
        users_to_seed = [
            {
                "email": "demo@legalai.com",
                "password": "DemoPassword2026!",
                "name": "Legal Intelligence Demo Evaluator",
            },
            {
                "email": "lawyer@example.com",
                "password": "SecurePassword123!",
                "name": "Senior Legal Counsel Demo",
            },
        ]

        seeded_users = {}
        for u_data in users_to_seed:
            user = db.query(User).filter(User.email == u_data["email"]).first()
            if not user:
                user = User(
                    email=u_data["email"],
                    hashed_password=hash_password(u_data["password"]),
                    is_active=True,
                    is_2fa_enabled=False,  # 2FA disabled for frictionless evaluation
                    data_retention_days=365,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"  [+] Created demo user: {u_data['email']} (Password: {u_data['password']})")
            else:
                # Update password hash and ensure active/unblocked
                user.hashed_password = hash_password(u_data["password"])
                user.is_active = True
                user.is_2fa_enabled = False
                db.commit()
                print(f"  [*] Updated existing user: {u_data['email']} (2FA disabled, password verified)")
            seeded_users[u_data["email"]] = user

        demo_user = seeded_users["demo@legalai.com"]

        # 3. Ensure uploads directory exists and write sample files
        upload_dir = Path(settings.UPLOAD_DIR).resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)

        contracts_meta = build_contract_data()
        seeded_contracts = {}

        for c_data in contracts_meta:
            key = c_data["key"]
            text_content = CONTRACT_TEXTS[key]
            disk_file = upload_dir / f"demo_{key}.txt"
            disk_file.write_text(text_content, encoding="utf-8")

            # Check if contract already exists for demo user
            contract = (
                db.query(Contract)
                .filter(Contract.user_id == demo_user.id, Contract.filename == c_data["filename"])
                .first()
            )
            if not contract:
                contract = Contract(
                    user_id=demo_user.id,
                    filename=c_data["filename"],
                    upload_path=str(disk_file),
                    status="analyzed",
                    created_at=datetime.now(timezone.utc) - timedelta(days=2),
                )
                db.add(contract)
                db.commit()
                db.refresh(contract)
                print(f"  [+] Seeded Contract #{contract.id}: {c_data['filename']}")
            else:
                contract.status = "analyzed"
                contract.upload_path = str(disk_file)
                db.commit()
                print(f"  [*] Updated Contract #{contract.id}: {c_data['filename']}")

            seeded_contracts[key] = contract

            # 4. Seed / Update 5 Analysis Records per contract
            def upsert_analysis(analysis_type: str, payload: Any):
                rec = (
                    db.query(Analysis)
                    .filter(Analysis.contract_id == contract.id, Analysis.analysis_type == analysis_type)
                    .first()
                )
                if rec:
                    rec.result_json = payload
                else:
                    rec = Analysis(
                        contract_id=contract.id,
                        analysis_type=analysis_type,
                        result_json=payload,
                    )
                    db.add(rec)

            # raw_text
            upsert_analysis("raw_text", {"text": text_content, "num_pages": 3, "char_count": len(text_content)})
            # parsing_agent
            upsert_analysis("parsing_agent", {
                "document_type": c_data["doc_type"],
                "party_a": c_data["parties"][0],
                "party_b": c_data["parties"][1],
                "effective_date": c_data["effective_date"],
                "jurisdiction": c_data["jurisdiction"],
                "summary": c_data["summary"],
            })
            # clauses (universal 9-clause checklist)
            upsert_analysis("clauses", c_data["clauses"])
            # risks (3-tier traffic-light system)
            upsert_analysis("risks", {"risks": c_data["risks"]})
            # compliance (8-domain statutory compliance findings)
            upsert_analysis("compliance", {"compliance_issues": c_data["compliance"]})
            # executive summary
            upsert_analysis("summary", {"summary": c_data["summary"]})

            db.commit()

        # 5. Seed Realistic Q&A Conversations with Pinpoint Citations
        conversations_to_seed = [
            {
                "contract_key": "saas_msa",
                "title": "Liability & Indemnity Risk Analysis",
                "turns": [
                    {
                        "role": "user",
                        "content": "Does this SaaS agreement have a monetary cap on liability, and does it protect against data loss?",
                        "citations": None,
                    },
                    {
                        "role": "assistant",
                        "content": "Yes. Under Section 5 (Limitation of Liability), each party's total aggregate liability is capped at the total fees paid or payable by Customer to Provider in the twelve (12) months preceding the event giving rise to liability.\n\nHowever, there is an important risk regarding data loss: Section 5 expressly disclaims liability for any indirect, incidental, consequential, special, or punitive damages, *specifically including loss of profits, data, or business interruption*. If Provider experiences a catastrophic database failure, Customer cannot recover consequential damages under this standard provision without negotiating a specific data protection carve-out.",
                        "citations": [
                            {
                                "clause_id": "liability_clauses",
                                "section": "Section 5",
                                "title": "Limitation of Liability",
                                "text": "EACH PARTY'S TOTAL AGGREGATE LIABILITY UNDER OR RELATING TO THIS AGREEMENT SHALL BE LIMITED TO THE TOTAL FEES PAID OR PAYABLE BY CUSTOMER TO PROVIDER IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO LIABILITY.",
                                "page": 1,
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": "Can CloudSphere increase subscription prices upon renewal?",
                        "citations": None,
                    },
                    {
                        "role": "assistant",
                        "content": "Yes. Under Section 3 (Term, Auto-Renewal and Cancellation), Provider reserves the unilateral right to increase annual subscription fees by up to 5% upon sixty (60) days prior written notice before renewal.\n\nRecommendation: If you wish to protect your budget, negotiate an amendment capping fee increases at the Consumer Price Index (CPI) or 3%, and ensure Customer retains the right to cancel without penalty if Provider gives notice of a fee increase.",
                        "citations": [
                            {
                                "clause_id": "renewal_clauses",
                                "section": "Section 3",
                                "title": "Term, Auto-Renewal and Cancellation",
                                "text": "Provider reserves the right to increase annual subscription fees by up to 5% upon sixty (60) days prior written notice before renewal.",
                                "page": 1,
                            }
                        ],
                    },
                ],
            },
            {
                "contract_key": "lease",
                "title": "Lock-in Period & Unilateral Arbitrator Inquiry",
                "turns": [
                    {
                        "role": "user",
                        "content": "What are our legal liabilities if we vacate the office space before the 3-year mark?",
                        "citations": None,
                    },
                    {
                        "role": "assistant",
                        "content": "Under Clause 1 (Lease Term and Lock-In Period), there is a strict mandatory lock-in period of thirty-six (36) months from August 1, 2026. If the Lessee vacates or terminates prior to the expiry of the lock-in period, the Lessee is liable to pay the entire rental for the remainder of the 36-month lock-in period as liquidated damages.\n\nAt INR 3,50,000/month, exiting at month 12 would trigger an immediate claim of INR 84 Lakhs (24 months × 3.5 Lakhs). Under Indian Contract law (Section 74 of the Indian Contract Act, 1872 and Kailash Nath Associates v. DDA), liquidated damages must represent a genuine pre-estimate of loss, but landlords frequently attempt to forfeit deposits and sue for the full lock-in balance. We strongly advise negotiating an early-exit break clause.",
                        "citations": [
                            {
                                "clause_id": "termination_clauses",
                                "section": "Clause 1",
                                "title": "Lease Term and Lock-In Period",
                                "text": "If the Lessee vacates or terminates the lease before the expiry of the lock-in period, the Lessee shall be liable to pay the entire rental for the remainder of the 36-month lock-in period as liquidated damages.",
                                "page": 1,
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": "Is the Lessor's sole arbitrator appointment clause legally binding?",
                        "citations": None,
                    },
                    {
                        "role": "assistant",
                        "content": "No. Under Clause 5, disputes are referred to a Sole Arbitrator appointed exclusively by the Lessor. Under Indian law (Section 12(5) read with the Seventh Schedule of the Arbitration and Conciliation Act, 1996, and the Supreme Court rulings in *TRF Ltd. v. Energo Engineering* and *Perkins Eastman Architects DPC v. HSCC (India) Ltd.*), an interested party or its nominee is ineligible to act as an arbitrator, and unilateral appointment of a sole arbitrator is void ab initio.\n\nThis clause cannot be enforced against you as written. However, to avoid litigation over appointment, amend Clause 5 to require mutual agreement or institutional appointment via the Bangalore Mediation Centre.",
                        "citations": [
                            {
                                "clause_id": "dispute_resolution_clauses",
                                "section": "Clause 5",
                                "title": "Dispute Resolution and Arbitration",
                                "text": "All disputes, controversies, or claims arising out of this Lease shall be referred to a Sole Arbitrator appointed exclusively by the Lessor.",
                                "page": 1,
                            }
                        ],
                    },
                ],
            },
            {
                "contract_key": "employment",
                "title": "Non-Compete Enforceability Review",
                "turns": [
                    {
                        "role": "user",
                        "content": "Is the 2-year post-termination non-compete clause legally enforceable in India?",
                        "citations": None,
                    },
                    {
                        "role": "assistant",
                        "content": "No. Under Section 4 (Post-Termination Non-Compete Covenant), the agreement purports to prohibit Dr. Sharma from working for any competing business in India for two (2) years following termination.\n\nUnder Section 27 of the Indian Contract Act, 1872, every agreement by which anyone is restrained from exercising a lawful profession, trade, or business of any kind is void to that extent. The Supreme Court of India (*Percept D'Mark (India) Pvt. Ltd. v. Zaheer Khan (2006)* and *Niranjan Shankar Golikari v. Century Spinning (1967)*) has settled that covenants in restraint of trade extending beyond the period of employment are void ab initio. The Company cannot legally prevent Dr. Sharma from joining a competitor post-employment, though confidentiality obligations regarding trade secrets remain enforceable.",
                        "citations": [
                            {
                                "clause_id": "non_compete_clauses",
                                "section": "Section 4",
                                "title": "Post-Termination Non-Compete Covenant",
                                "text": "Executive agrees that for a period of two (2) years following the termination of employment for any reason, Executive shall not... engage in, work for, or provide advisory services to any competing business... in the territory of India.",
                                "page": 1,
                            }
                        ],
                    },
                ],
            },
        ]

        for conv_data in conversations_to_seed:
            contract = seeded_contracts[conv_data["contract_key"]]
            # Check if conversation already exists
            existing_conv = (
                db.query(Conversation)
                .filter(
                    Conversation.user_id == demo_user.id,
                    Conversation.contract_id == contract.id,
                    Conversation.title == conv_data["title"],
                )
                .first()
            )
            if existing_conv:
                db.delete(existing_conv)
                db.commit()

            conv = Conversation(
                user_id=demo_user.id,
                contract_id=contract.id,
                title=conv_data["title"],
                created_at=datetime.now(timezone.utc) - timedelta(hours=12),
                last_message_at=datetime.now(timezone.utc) - timedelta(hours=11),
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)

            for idx, turn in enumerate(conv_data["turns"]):
                msg = ConversationMessage(
                    conversation_id=conv.id,
                    role=turn["role"],
                    content=turn["content"],
                    cited_clause_refs=turn["citations"],
                    created_at=datetime.now(timezone.utc) - timedelta(hours=12 - idx),
                )
                db.add(msg)
            db.commit()
            print(f"  [+] Seeded Conversation #{conv.id} ({conv.title}) on Contract #{contract.id}")

        # 6. Seed Realistic Audit Logs for Activity Timeline
        sample_audit_events = [
            (AuditEventType.USER_REGISTERED, None, "SUCCESS", {"method": "password", "email": demo_user.email}, 48),
            (AuditEventType.USER_LOGIN, None, "SUCCESS", {"method": "password", "device": "Chrome / macOS"}, 47),
            (AuditEventType.CONTRACT_UPLOADED, seeded_contracts["nda"].id, "SUCCESS", {"filename": "Mutual_Non_Disclosure_Agreement_Apex_Nexus.pdf", "size_bytes": 14200}, 46),
            (AuditEventType.ANALYSIS_STARTED, seeded_contracts["nda"].id, "SUCCESS", {"mode": "multi_agent_dialect"}, 45),
            (AuditEventType.ANALYSIS_COMPLETED, seeded_contracts["nda"].id, "SUCCESS", {"latency_ms": 3200, "doc_type": "Non-Disclosure Agreement (NDA)"}, 45),
            (AuditEventType.CONTRACT_UPLOADED, seeded_contracts["saas_msa"].id, "SUCCESS", {"filename": "Master_Cloud_Services_Agreement_CloudSphere.pdf", "size_bytes": 18400}, 40),
            (AuditEventType.ANALYSIS_COMPLETED, seeded_contracts["saas_msa"].id, "SUCCESS", {"latency_ms": 4100, "doc_type": "Master Services Agreement (MSA)"}, 39),
            (AuditEventType.QA_MESSAGE_SENT, seeded_contracts["saas_msa"].id, "SUCCESS", {"query": "Does this SaaS agreement have a monetary cap on liability?", "citations_count": 1}, 38),
            (AuditEventType.CONTRACT_UPLOADED, seeded_contracts["employment"].id, "SUCCESS", {"filename": "Executive_Employment_Agreement_Dr_Sharma.pdf", "size_bytes": 16100}, 30),
            (AuditEventType.ANALYSIS_COMPLETED, seeded_contracts["employment"].id, "SUCCESS", {"latency_ms": 3800, "doc_type": "Executive Employment Agreement"}, 29),
            (AuditEventType.QA_MESSAGE_SENT, seeded_contracts["employment"].id, "SUCCESS", {"query": "Is the 2-year post-termination non-compete clause legally enforceable?", "citations_count": 1}, 28),
            (AuditEventType.CONTRACT_UPLOADED, seeded_contracts["lease"].id, "SUCCESS", {"filename": "Commercial_Indenture_of_Lease_Horizon_Omni.pdf", "size_bytes": 22400}, 20),
            (AuditEventType.ANALYSIS_COMPLETED, seeded_contracts["lease"].id, "SUCCESS", {"latency_ms": 4600, "doc_type": "Commercial Lease Agreement"}, 19),
            (AuditEventType.QA_MESSAGE_SENT, seeded_contracts["lease"].id, "SUCCESS", {"query": "What are our legal liabilities if we vacate the office space?", "citations_count": 1}, 18),
            (AuditEventType.CONTRACT_UPLOADED, seeded_contracts["freelance"].id, "SUCCESS", {"filename": "Independent_Contractor_Consulting_Agreement_Apex_Verma.pdf", "size_bytes": 19500}, 10),
            (AuditEventType.ANALYSIS_COMPLETED, seeded_contracts["freelance"].id, "SUCCESS", {"latency_ms": 3900, "doc_type": "Consulting & Services Agreement"}, 9),
            (AuditEventType.SEARCH_PERFORMED, None, "SUCCESS", {"query": "uncapped indemnification or liability", "results_count": 4}, 5),
            (AuditEventType.CONTRACT_VIEWED, seeded_contracts["freelance"].id, "SUCCESS", {"duration_seconds": 180}, 2),
        ]

        # Clear existing seeded demo audit logs for clean timeline
        db.query(AuditLog).filter(AuditLog.user_id == demo_user.id).delete()
        db.commit()

        for action, resource_id, status, meta, hours_ago in sample_audit_events:
            log_entry = AuditLog(
                user_id=demo_user.id,
                action=action,
                resource_id=resource_id,
                status=status,
                ip_address="192.168.1.105",
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                metadata_json=meta,
                timestamp=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
            )
            db.add(log_entry)
        db.commit()
        print(f"  [+] Seeded {len(sample_audit_events)} Audit Logs for demo user activity history")

        # 7. Seed identical contracts for lawyer@example.com for secondary demo login
        alt_user = seeded_users["lawyer@example.com"]
        for c_data in contracts_meta:
            existing_c = (
                db.query(Contract)
                .filter(Contract.user_id == alt_user.id, Contract.filename == c_data["filename"])
                .first()
            )
            if not existing_c:
                c = Contract(
                    user_id=alt_user.id,
                    filename=c_data["filename"],
                    upload_path=str(upload_dir / f"demo_{c_data['key']}.txt"),
                    status="analyzed",
                )
                db.add(c)
                db.commit()
                db.refresh(c)
                # Clone analysis records
                for a_type in ["raw_text", "parsing_agent", "clauses", "risks", "compliance", "summary"]:
                    source_a = (
                        db.query(Analysis)
                        .filter(Analysis.contract_id == seeded_contracts[c_data["key"]].id, Analysis.analysis_type == a_type)
                        .first()
                    )
                    if source_a:
                        db.add(Analysis(contract_id=c.id, analysis_type=a_type, result_json=source_a.result_json))
                db.commit()
        print(f"  [+] Seeded contracts and analyses for alternative user: lawyer@example.com")

        print("=" * 60)
        print("✅ DEMO SEEDING COMPLETED SUCCESSFULLY!")
        print("   Primary Demo Login:     demo@legalai.com / DemoPassword2026!")
        print("   Alternative Demo Login: lawyer@example.com / SecurePassword123!")
        print("   Contracts Seeded:       5 realistic contracts across diverse domains")
        print("   Q&A Threads Seeded:     3 conversations with pinpoint clause citations")
        print("   Audit Logs Seeded:      18 activities recorded on timeline")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"❌ Error during demo seeding: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
