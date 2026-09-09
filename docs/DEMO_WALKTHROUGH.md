# 3-Minute Video Demo Walkthrough Script
## AI Legal Document Intelligence Platform

**Target Duration:** Exactly 3 Minutes (180 Seconds)  
**Target Audience:** Engineering Hiring Managers, Tech Leads, Legal Tech Founders  
**Presenter:** Nipun Chugh  
**Demo URL:** `http://localhost:3000` (Local) or [Hugging Face Space](https://huggingface.co/spaces/Nipunchugh10/AI-Legal-Document-Intelligence-Platform)  

---

## Quick Reference Timestamp Grid

| Time | Segment Name | Visual Focus | Core Message |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:25** | **The Hook & 1-Click Access** | Login page, "⚡ Try Demo" button | Why generic ChatGPT fails legal review; 1-click evaluation |
| **0:25 – 0:55** | **Multimodal Ingestion** | Dashboard & Upload page | PDF/scanned OCR/DOCX ingestion with metadata extraction |
| **0:55 – 1:35** | **Multi-Agent Dialectics** | Contract Detail workspace | 9-clause checklist, 3-tier traffic-light risks & redline tips |
| **1:35 – 2:10** | **Grounded Q&A & Citations** | Q&A interface & citation drawer | Zero hallucinations, verbatim source clause highlighting |
| **2:10 – 2:35** | **Comparison & Semantic Search** | `/contracts/compare` & `/search` | Cross-contract side-by-side diffs & portfolio vector search |
| **2:35 – 3:00** | **Security & Forensic Audit** | `/history` and `/security` | GDPR export, Email OTP 2FA, 378 passing tests, 100% Free Tier |

---

## Detailed Script & Presenter Talk Track

### [0:00 – 0:25] Segment 1: The Problem Hook & 1-Click Instant Access
**Visual:** Screen begins on the platform login page (`/login`). Move mouse over the login credentials card.  
**Presenter Talk Track:**
> *"Hi everyone, I'm Nipun. Today, legal counsel spends 4 to 8 hours manually reviewing a single 30-page commercial contract. Generic AI models like ChatGPT sound convincing, but they hallucinate legal precedents, miss statutory compliance, and fail to cite verbatim sources.*
>
> *I built the **AI Legal Document Intelligence Platform** to solve this. Notice on the login screen, we've implemented a **1-click '⚡ Try Demo' access button**, allowing reviewers and recruiters to explore the platform with zero friction."*
*(Click "⚡ Try Demo" — instantly redirects to `/dashboard`)*

---

### [0:25 – 0:55] Segment 2: Portfolio Dashboard & Multimodal Ingestion
**Visual:** The dashboard loads showing the pre-seeded portfolio of 5 diverse contracts (NDA, SaaS MSA, Employment Agreement, Lease, Consulting). Navigate to `/contracts/upload`.  
**Presenter Talk Track:**
> *"Here on the dashboard, we see a portfolio of contracts across key enterprise domains. In the upload workspace, the platform accepts native PDFs, scanned image PDFs via Google Gemini Vision OCR, and DOCX agreements.*
>
> *Upon upload, our asynchronous ingestion pipeline cleans the text, parses parties and jurisdiction, and indexes semantic embeddings into ChromaDB in under 50 milliseconds."*

---

### [0:55 – 1:35] Segment 3: Multi-Agent Analysis & 9-Clause Checklist
**Visual:** Click on `Master_Cloud_Services_Agreement_CloudSphere.pdf`. Scroll through the analysis tabs: Overview, Clauses, Risks, Compliance, and Summary.  
**Presenter Talk Track:**
> *"Under the hood, a **LangGraph state machine orchestrates 5 specialized legal agents**:*
>
> *First, our **Clause Agent** benchmarks the contract against a universal **9-clause checklist**—verifying Confidentiality, Indemnity, Liability Caps, and Termination.*
>
> *Second, our **Risk Agent** uses the legal IRAC framework to categorize risks into a **3-tier traffic-light system**. Notice this Red Flag on Section 10: unlimited uncapped liability. The agent doesn't just flag it—it counter-drafts a concrete redline revision and negotiation talk track.*
>
> *Third, our **Compliance Agent** runs RAG over 8 statutory domains, instantly identifying whether a non-compete is void under Section 27 of the Indian Contract Act or whether a DPA complies with GDPR Article 28."*

---

### [1:35 – 2:10] Segment 4: Grounded Q&A with Pinpoint Clause Citations
**Visual:** Click "Ask Legal Question" button to navigate to `/contracts/2/ask`. Type: *"What is the governing law and arbitration venue?"* Submit query. Click on the resulting citation reference pill.  
**Presenter Talk Track:**
> *"Now let's ask a complex legal question in our Q&A interface. Notice the response: it answers in clear English, but more importantly, it includes an interactive **pinpoint clause citation**.*
>
> *Clicking the citation drawer reveals the exact verbatim text snippet and chunk coordinates from Article 13 of the agreement. If a term is not in the contract, the agent strictly responds 'Not mentioned in contract', providing zero-hallucination guardrails."*

---

### [2:10 – 2:35] Segment 5: Side-by-Side Comparison & Semantic Search
**Visual:** Navigate to `/contracts/compare`. Select Contract A and Contract B to show the diff table. Then navigate to `/search` and type *"indemnification super-cap"*.  
**Presenter Talk Track:**
> *"For M&A or vendor renewals, our **Contract Comparison Engine** renders side-by-side clause alignment, highlighting differences in cure periods, caps, and governing laws.*
>
> *And our **Semantic Search Engine** allows legal teams to query across their entire portfolio using natural language rather than brittle keyword matching."*

---

### [2:35 – 3:00] Segment 6: Enterprise Security, Audit Trail & Conclusion
**Visual:** Navigate to `/history` to show the audit trail timeline, then click `/security` to show sessions and GDPR data export button.  
**Presenter Talk Track:**
> *"Finally, security is built in from day one: zero-trust multi-tenancy, SHA-256 Email OTP two-factor authentication, 40-minute inactivity auto-logout, and an append-only forensic audit log on the `/history` timeline.*
>
> *Users have complete data sovereignty with one-click **GDPR Article 20 JSON data export** and cascade account deletion.*
>
> *The entire system is covered by **378 automated tests with a 100% pass rate** on GitHub Actions, running entirely on a 100% Free-Tier cloud infrastructure. Thanks for watching!"*

---

## Tips for Recording the Video
1. **Screen Resolution:** Record at 1920x1080 (1080p), 60fps.
2. **Audio:** Use a clean external microphone with noise suppression.
3. **Cursor:** Keep cursor movements smooth and intentional; highlight UI buttons before clicking.
4. **Theme:** Use the platform's dark mode theme for high contrast.
