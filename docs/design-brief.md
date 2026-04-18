## Design Brief: Inspectra SaaS Dashboard

**Project Name:** E-State  
**Industry:** GovTech / Real Estate Data Management  
**Objective:** Create a high-fidelity, minimal SaaS dashboard for municipal employees to identify and reconcile discrepancies between land registry datasets.

---

### 🏛 Project Overview
E-State is a specialized tool designed to streamline the audit process of municipal land records. The UI must transition from a "data dump" feel to an actionable, professional tool that prioritizes clarity and high-stakes decision-making.

### 🎨 Visual Identity & Style Guide
The aesthetic should be clean and "production-ready," avoiding the cluttered look often found in legacy government software.

* **Theme:** Light, minimal, and modern.
* **Color Palette:**
    * **Primary (Actions):** `#3F5E3B` (Deep Forest Green)
    * **Accent (Secondary):** `#B6B774` (Muted Olive)
    * **Background Blocks:** `#E3C9A9` (Warm Sand)
    * **Alert/Highlight:** `#C97A7F` (Dusty Rose/Red)
    * **Surface:** `#FFFFFF` or very light grey.
* **UI Components:** Rounded corners (8px–12px), soft depth shadows, and generous whitespace.
* **Typography:** High-legibility sans-serif (e.g., Inter or Public Sans) to ensure data scanning is effortless.

---

### 🗺 Information Architecture & Key Views

#### 1. Main Dashboard (“E-state”)
The entry point for the user, providing a high-level birds-eye view of the system's current status.
* **Header:** Title “E-state” with subtitle “Asset discrepancy detection system.”
* **Metrics Row:**
    * **Total Records:** Overall count of entries in the system.
    * **Mismatches Found:** Highlighting the scope of work needed.
    * **Files Processed:** Historical data volume.
* **Primary CTA:** Large “Upload Data” button to initiate the workflow.

#### 2. Upload Interface
A focused, distraction-free area for data ingestion.
* **Drop Zone:** A clean drag-and-drop area for CSV/Excel files.
* **Feedback Loop:** Visual indicators for "Uploaded" vs. "Ready for Analysis."
* **Action:** "Start Analysis" button to trigger the backend processing.

#### 3. Analysis Results (The "Workhorse" View)
This page must handle dense information without becoming overwhelming.
* **Summary Tier:** Three cards for **Total Mismatches**, **Critical Issues**, and **Warnings**.
* **Data Table:**
    * Columns for Address, Owner A/B, Area A/B, and Status.
    * **Status Badges:** Use the color logic (Red: Critical, Yellow: Warning, Green: Match).
* **Control Layer:** A filter dropdown to sort by mismatch severity or type.

#### 4. Record Details (Deep Dive)
A side-by-side comparison view used to finalize decisions.
* **Layout:** Split-screen or two-column comparison (Registry A vs. Registry B).
* **Highlighting:** Automated red highlighting on specific fields where data points diverge.
* **Status Label:** Prominent “Mismatch detected” banner for quick context.

---

### ⚡ UX & Functional Priorities
* **Scannability:** Users should be able to identify "Critical" issues within 3 seconds of page load.
* **Hierarchy:** Use the `#3F5E3B` primary color to lead the eye toward the most important buttons (Upload/Start/Resolve).
* **Trust:** The UI must look official and secure, leveraging the "Background Blocks" (`#E3C9A9`) to separate UI sections without using harsh borders.
* **Demo-Readiness:** Ensure the layout remains balanced even with varying lengths of addresses or names.

---

### 🛠 Tech Stack Recommendation (Development)
* **Frontend:** React or Next.js with Tailwind CSS for rapid styling.
* **Icons:** Lucide-React or Phosphor Icons for a thin, modern stroke weight.
* **Components:** Radix UI or Shadcn/ui for accessible, pre-built accessible primitives (Tables, Dialogs, Badges).