---
name: Industrial Precision Management
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1b1c1c'
  on-surface-variant: '#5b403d'
  inverse-surface: '#303030'
  inverse-on-surface: '#f3f0ef'
  outline: '#8f706c'
  outline-variant: '#e4beb9'
  surface-tint: '#b91d1d'
  primary: '#91000a'
  on-primary: '#ffffff'
  primary-container: '#b71c1c'
  on-primary-container: '#ffcac4'
  inverse-primary: '#ffb4ab'
  secondary: '#5d5f5f'
  on-secondary: '#ffffff'
  secondary-container: '#dfe0e0'
  on-secondary-container: '#616363'
  tertiary: '#444646'
  on-tertiary: '#ffffff'
  tertiary-container: '#5c5d5d'
  on-tertiary-container: '#d6d6d6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad6'
  primary-fixed-dim: '#ffb4ab'
  on-primary-fixed: '#410002'
  on-primary-fixed-variant: '#93000b'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c7'
  on-secondary-fixed: '#1a1c1c'
  on-secondary-fixed-variant: '#454747'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c7'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#fcf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e5e2e1'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  button:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.1px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  edge_margin: 16px
  gutter: 12px
---

## Brand & Style

This design system is engineered for high-stakes enterprise environments where speed, accuracy, and clarity are paramount. The brand personality is authoritative yet unobtrusive, focusing on task completion within warehouses and retail floors. 

The aesthetic follows a **Modern Enterprise** approach, heavily influenced by **Material Design 3 (MD3)** principles. It prioritizes a clean, white-dominant interface to maximize legibility under various lighting conditions. By utilizing a "Redline" primary color against a stark white and light gray backdrop, the UI directs focus to critical actions and status indicators. The emotional response is one of reliability and systematic efficiency, reducing cognitive load during intensive stock-counting sessions.

## Colors

The palette is anchored by **Deep Red**, used strategically for primary actions, branding, and high-priority states. 

- **Primary (#B71C1C):** Reserved for the "Primary Action Button" (FAB), active tab indicators, and critical selection states.
- **Surface & Background:** The application utilizes a pure white (#FFFFFF) background to maintain high contrast with text. 
- **Accent/Muted (#F5F5F5):** Used for non-interactive containers, search bars, and background fills for grouped list items to provide subtle visual separation without adding weight.
- **Semantic Colors:** Success (Green), Warning (Orange), and Error (Red) are used exclusively for stock status (e.g., "In Stock," "Low Stock," "Out of Sync") and input validation.

## Typography

The design system utilizes **Inter** for its exceptional legibility on mobile screens and neutral, professional tone. 

- **Headlines:** Use tighter letter-spacing and heavier weights to create a clear hierarchy for SKU names and Section titles.
- **Body Text:** Standard weight for descriptions and data values to ensure long-term reading comfort during audits.
- **Data Labels:** **JetBrains Mono** is introduced for alphanumeric strings like Barcodes, Serial Numbers, and Location IDs. This monospaced font prevents character confusion (e.g., '0' vs 'O') which is critical in inventory management.
- **Accessibility:** Minimum touch target text size is 14px. Secondary information never drops below 12px.

## Layout & Spacing

The system operates on a **strict 8px grid**. All components, margins, and paddings are multiples of 8, ensuring a rhythmic and predictable vertical flow.

- **Mobile Layout:** A single-column fluid layout with a standard **16px side margin**.
- **Touch Targets:** All interactive elements (buttons, list items, checkboxes) must have a minimum height of **48px** to accommodate gloved hands or rapid movement.
- **Card Spacing:** Vertical stacks of inventory items use a 12px gutter to maintain distinct separation while maximizing vertical real estate.

## Elevation & Depth

In alignment with Material 3, depth is used to communicate interactivity and hierarchy.

- **Level 0 (Flat):** The main background surface.
- **Level 1 (Tonal):** Cards and search inputs. These use a subtle 1px border (#E0E0E0) and no shadow when "at rest" to maintain a clean look.
- **Level 2 (Raised):** Used for active inventory items during a count. Characterized by a soft, diffused shadow (Y: 4, Blur: 12, Opacity: 0.08, Color: #000000).
- **Level 3 (Overlay):** Floating Action Buttons (FAB) and Modals. These use a more pronounced shadow (Y: 8, Blur: 24, Opacity: 0.12) to indicate they are at the top of the stack.

## Shapes

The shape language is **Extra Rounded**, designed to soften the "industrial" nature of the application and make it feel modern and approachable.

- **Cards:** Use a consistent **16px (rounded-lg)** corner radius.
- **Buttons:** Use a **24px (fully rounded/pill)** shape for primary actions to distinguish them from data cards.
- **Input Fields:** Use a **12px** radius to balance the squareness of the screen with the roundness of the cards.

## Components

### Buttons
- **Primary:** Deep Red fill with White text. High-emphasis. Fully rounded.
- **Secondary:** White fill with Deep Red border (1px). Medium-emphasis.
- **Tertiary:** Text-only, Deep Red, for less frequent actions like "Cancel" or "View Details."

### Inventory Cards
The core component of the system.
- **Layout:** SKU/Name (Top Left), Quantity (Top Right), Location (Bottom Left), Status Badge (Bottom Right).
- **State Feedback:** When an item is "Counted," the card border changes to Success Green (2px).

### Status Badges
- Small, rounded containers with low-opacity fills of the semantic colors (e.g., Light Green fill with Dark Green text). Used for "In Stock," "Low," or "Damaged."

### Input Fields
- Outlined style with 16px horizontal padding. The label should float to the top border on focus (MD3 style). Use the monospaced font for the input text when entering numeric quantities.

### Floating Action Button (FAB)
- A large, circular button in the bottom right corner for the primary "Scan Barcode" action. Uses the Primary Red color and a white icon.