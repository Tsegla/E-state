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
* **UI Components:** Rounded corners **(10px for inputs/buttons, 14px–18px for cards, 24px for hero tiles)**, soft depth shadows (`shadow-card`, `shadow-elevated`), and generous whitespace.
* **Header:** Sticky, pure-white surface with a 36×36 forest-green logo tile (white building glyph). Nav items are rounded-xl pills; the active route is a filled forest-green pill with white text.
* **Section eyebrow label:** Every primary page header is preceded by a small `11px uppercase tracking-wide` muted label (e.g. "DATA INGESTION", "CROSS-REGISTRY REPORT") to orient the user.
* **Metric tiles:** White surface, 40×40 tinted icon tile top-left, top-right uppercase badge/meta, value in 30px semibold, sub-label and hint in muted ink.
* **Hero tiles:** The "Detection rate" card uses a solid forest-green background with white type; the "Last analysis" card uses the warm-sand block.
* **Status badges:** Rounded-full chip with a 6px leading colored dot (Match = forest, Warning = amber, Critical = rose, Info = blue).
* **Typography:** High-legibility sans-serif (Inter) with `cv11`/`ss01` features, tabular numerals for all metrics.

---

### 🗺 Information Architecture & Key Views

#### 1. Main Dashboard (“E-state”)
The entry point for the user, providing a high-level birds-eye view of the system's current status.
* **Header:** Eyebrow label + title "E-state" + subtitle "Система виявлення розбіжностей" and a forest-green "Upload data" CTA (large size, trailing arrow) on the right.
* **Metrics Row (3 tiles):**
    * **Total Records:** Overall count of entries in the system (icon tile, "Last sync today" badge).
    * **Mismatches Found:** Highlighted in rose with detection-rate % badge.
    * **Files Processed:** Historical data volume with dataset count badge.
* **Content row:** Two-column split.
    * Left: "Recent Discrepancies" card — list of up to 3 findings with severity dot badges and hover-reveal `ArrowUpRight` glyph; footer row deep-links to the full findings list.
    * Right stack: Filled forest-green "Detection rate" hero tile (very large % value in white) and a warm-sand "Last analysis" tile with a secondary CTA.

#### 2. Upload Interface
A focused, distraction-free area for data ingestion.
* **Drop Zones:** Two side-by-side dashed rounded-2xl tiles (ДЗК / ДРРП) with a 48×48 sand/forest icon tile (FolderUp → CheckCircle2 once a file is selected) and the chosen filename displayed in forest-700 once assigned.
* **Feedback Loop:** Footer status ("Обрано файлів: 1/2") + inline amber info notice reminding the user to attach both registry exports.
* **Action:** Right-aligned large "Upload & run matcher" button with a trailing arrow.

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