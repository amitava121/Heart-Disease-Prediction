# Design System Specification: The Clinical Ethereal

## 1. Creative North Star: "The Pulse of Precision"
The "Pulse of Precision" philosophy rejects the sterile, flat aesthetic of traditional medical portals in favor of a high-end, editorial experience. This design system treats data as a living entity. We move away from rigid, boxed layouts and toward a "layered intelligence" model. 

By utilizing intentional asymmetry, overlapping frosted surfaces, and deep tonal depth, we create an environment that feels both cutting-edge (technological) and reassuring (human). The goal is to evoke the feeling of a high-end medical laboratory at night—focused, calm, and illuminated by the soft glow of advanced diagnostics.

## 2. Colors & Surface Architecture
Our palette is rooted in the deep shadows of the cardiovascular system, illuminated by the "electric life" of the heart.

### The Palette (Material Design Tokens)
*   **Core Background:** `surface` (#0e1322) – A deep, immersive navy.
*   **Primary Accent:** `primary` (#98cbff) – A cool, clinical blue.
*   **Secondary Accent:** `secondary` (#ffabf3) – A vibrant magenta representing vitality.
*   **Tertiary Accent:** `tertiary` (#d1bcff) – Soft lavender for supplemental data.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to define sections. Layout boundaries must be defined solely through background color shifts or tonal transitions. 
*   Use `surface-container-low` (#161b2b) for secondary sections sitting on a `surface` background.
*   Use `surface-container-highest` (#2f3445) to draw the eye to interactive data widgets.

### The "Glass & Gradient" Rule
To achieve a premium, custom feel, floating elements (modals, navigation bars, hover states) must utilize **Glassmorphism**:
*   **Fill:** `surface-variant` (#2f3445) at 40-60% opacity.
*   **Effect:** Backdrop-blur (12px to 20px).
*   **Signature Gradients:** For high-impact CTAs, use a linear gradient transitioning from `primary` (#98cbff) to `primary_container` (#0097ec) at a 135-degree angle. This adds "soul" and prevents the UI from feeling static.

## 3. Typography: Editorial Authority
We pair the geometric precision of **Manrope** for high-level communication with the hyper-legibility of **Inter** for clinical data.

*   **Display (Manrope):** Large, airy, and authoritative. Use `display-lg` (3.5rem) for hero statements with tight letter-spacing (-0.02em).
*   **Headlines (Manrope):** Use `headline-md` (1.75rem) to introduce new data sections. These should feel like titles in a premium medical journal.
*   **Body & Labels (Inter):** All functional data, heart rate metrics, and prediction results use Inter. Use `body-md` (0.875rem) for general descriptions and `label-md` (0.75rem) for micro-copy or 3D icon captions.
*   **Visual Hierarchy:** Establish "Typographic Breathing Room." Headers should often have 1.5x more margin-bottom than standard grids to allow the "Glass" surfaces to feel expansive.

## 4. Elevation & Depth
In this system, depth is a tool for diagnostic priority.

*   **Tonal Layering Principle:** Stacking is the new bordering. Place a `surface-container-lowest` (#090e1c) card inside a `surface-container-low` (#161b2b) section to create a "recessed" look. Conversely, use `surface-bright` (#343949) for active, elevated states.
*   **Ambient Shadows:** Traditional black shadows are forbidden. If a floating effect is required, use a shadow color tinted with `on-surface` (#dee1f7) at 6% opacity with a 40px blur. It should feel like an "aura" rather than a drop shadow.
*   **The Ghost Border:** For accessibility on inputs, use `outline-variant` (#414754) at 15% opacity. It should be barely perceptible, serving as a hint of structure rather than a hard wall.

## 5. Components & Signature Patterns

### Buttons (Vitality Triggers)
*   **Primary:** A gradient-filled container (`primary` to `primary_container`) with `on_primary` text. No border. Roundedness: `lg` (1rem).
*   **Secondary:** Glassmorphic fill with a "Ghost Border" of `primary` at 20% opacity.
*   **Tertiary:** Transparent background, `primary` text, with an underline that appears only on hover.

### 3D Diagnostic Cards
*   **Layout:** Never use dividers. Separate heart metrics (BP, Cholesterol, etc.) using generous vertical spacing.
*   **Iconography:** Incorporate 3D medical icons with soft, internal glows that match the `secondary` magenta or `primary` blue palette.
*   **Background:** Use `surface-container` (#1a1f2f) with a `xl` (1.5rem) corner radius.

### Input Fields (Clinical Entry)
*   **State:** The default state is a subtle `surface-container-highest` (#2f3445) fill.
*   **Focus State:** The "Ghost Border" transitions to 100% opacity `primary` blue with a 2px outer glow (0% to 10% opacity).

### Predictive Progress Chips
*   For heart disease risk levels (Low, Moderate, High), use `tertiary_container` for the background and `on_tertiary_container` for the text. Ensure the chip has a glassmorphic blur to feel "integrated" into the data dashboard.

## 6. Do’s and Don’ts

### Do:
*   **Do** embrace asymmetry. Let a 3D heart model bleed off the edge of a glass container.
*   **Do** use `secondary` (magenta) sparingly to highlight critical health alerts or "High Risk" predictions.
*   **Do** ensure text on glass surfaces meets AA contrast ratios by adjusting the backdrop-blur intensity.

### Don’t:
*   **Don’t** use 100% white (#ffffff). Use `on_surface` (#dee1f7) for high-contrast text to reduce eye strain in dark mode.
*   **Don’t** use standard Material Design "elevated" shadows. They feel "cheap" in an editorial context. Stick to tonal shifts.
*   **Don’t** use sharp corners. Every interactive element must use a minimum of `md` (0.75rem) roundedness to maintain a high-trust, organic feel.