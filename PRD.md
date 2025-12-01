# Planning Guide

A comprehensive inventory management system for mobile phones and accessories designed for sales chatbot integration, featuring real-time stock tracking, order processing, multi-profile support, and flexible backend connectivity (local storage or FastAPI backend).

**Experience Qualities**: 
1. **Efficient** - Streamlined workflows that allow quick product lookup and order creation with minimal clicks
2. **Reliable** - Clear stock indicators and validation messages ensure accurate inventory management
3. **Professional** - Clean, business-focused interface that inspires confidence in the data presented

**Complexity Level**: Light Application (multiple features with basic state)
  - The app manages products, inventory, orders, and profiles with persistent state, supports both local and API backends, but doesn't require user authentication or complex workflows beyond CRUD operations.

## Essential Features

### Dashboard Statistics
- **Functionality**: Display key metrics for active products, orders, inventory value, and low/out-of-stock alerts
- **Purpose**: Provides at-a-glance overview of business health and critical inventory issues
- **Trigger**: Automatically displayed on products tab
- **Progression**: View dashboard → See real-time statistics → Identify issues quickly
- **Success criteria**: Stats update in real-time, accurate calculations, clear visual hierarchy

### Backend Connectivity
- **Functionality**: Toggle between local browser storage and FastAPI backend API with configurable endpoint
- **Purpose**: Allows users to start with local storage and migrate to production backend when ready
- **Trigger**: User clicks settings icon in header
- **Progression**: Open settings → Toggle API mode → Configure API URL → Test connection → Save → Reload page to apply changes
- **Success criteria**: Connection test validates endpoint, smooth transition between backends, data persists correctly in selected backend

### Product Catalog Management
- **Functionality**: Display searchable list of products with detailed specifications (brand, model, capacity, condition, price, warranty)
- **Purpose**: Enables quick product lookup for sales operations and chatbot integrations
- **Trigger**: User navigates to products view or performs search
- **Progression**: View products list → Apply filters (profile, search term, category) → See filtered results with stock levels → Select product for details
- **Success criteria**: Products filter in <100ms, stock levels accurately reflect inventory, search matches name/brand/model

### Order Creation & Processing
- **Functionality**: Create new orders with product selection, customer info, and payment method tracking
- **Purpose**: Record sales transactions and automatically update inventory levels
- **Trigger**: User clicks "New Order" button
- **Progression**: Click new order → Select profile & channel → Enter customer details → Add products with quantities → Validate stock availability → Confirm order → Stock automatically decremented
- **Success criteria**: Orders save with all line items, stock decreases atomically, validation prevents overselling

### Multi-Profile Support
- **Functionality**: Support multiple business profiles (stores/brands) with isolated product catalogs and customizable settings per profile
- **Purpose**: Allow single system to manage inventory for different business entities with independent configurations (currency, taxes, business info)
- **Trigger**: User selects profile from dropdown, creates new profile, or accesses profile settings
- **Progression**: Select profile → View profile-specific products → Create profile-specific orders → Configure profile settings → Switch profiles → See different data with appropriate settings applied
- **Success criteria**: Products and orders correctly filtered by profile, no data leakage between profiles, profile settings persist and apply correctly, slug validation prevents duplicates, setup guide helps new users understand multi-profile system

### Real-Time Stock Tracking
- **Functionality**: Display current stock levels and prevent orders exceeding available inventory
- **Purpose**: Maintain accurate inventory counts and prevent overselling
- **Trigger**: Product display, order creation attempt
- **Progression**: View product → See current stock → Attempt order → Validate quantity → Show error if insufficient or confirm if available
- **Success criteria**: Stock displays accurately, validation prevents negative stock, updates persist across sessions

### Order History & Status
- **Functionality**: View all orders with status tracking (pending, ready to deliver, completed, cancelled) and filtering by status
- **Purpose**: Monitor sales pipeline and order fulfillment progress
- **Trigger**: User navigates to orders view or changes status filter
- **Progression**: View orders → Filter by status/profile → See order details → Update order status → History updates
- **Success criteria**: Orders display with correct totals, status updates save, filtering works correctly

### Data Export
- **Functionality**: Export products and orders to CSV format for external analysis
- **Purpose**: Enable reporting, accounting, and data analysis in external tools
- **Trigger**: User clicks export button in products or orders tab
- **Progression**: Click export → Data formatted to CSV → File downloaded with timestamp → Success notification
- **Success criteria**: CSV includes all visible filtered data, proper formatting, unique filenames with dates

### Analytics Dashboard (Enhanced)
- **Functionality**: Visual dashboard with charts showing sales trends, revenue, top products, and order distribution
- **Purpose**: Provide business insights at a glance to support data-driven decisions
- **Trigger**: Automatically displayed on products tab
- **Progression**: View dashboard → See KPI cards → Review charts for trends → Identify opportunities or issues
- **Success criteria**: Charts render correctly, data updates in real-time, responsive on all devices, clear visual hierarchy

### Profile Management (Enhanced)
- **Functionality**: Create, edit, activate/deactivate business profiles with full settings customization
- **Purpose**: Allow full lifecycle management of business entities within the system with independent configurations
- **Trigger**: User clicks edit button on profile card, settings button, or creates new profile
- **Progression**: Navigate to Profiles → View existing profiles or setup guide → Create new profile with validated slug → Configure profile settings (currency, taxes, business info) → Edit profile name or status → Manage products and orders per profile
- **Success criteria**: Profile updates persist, inactive profiles can be filtered, slug remains immutable after creation, settings apply to profile operations, validation prevents duplicate slugs, helpful guide shown for single-profile users

### Keyboard Shortcuts
- **Functionality**: Quick navigation and actions using keyboard combinations
- **Purpose**: Increase efficiency for power users managing inventory frequently
- **Trigger**: User presses keyboard shortcut or clicks keyboard icon in header
- **Progression**: Press shortcut → Action executed immediately → Visual feedback provided
- **Success criteria**: All shortcuts work reliably, help dialog accessible, shortcuts documented

## Edge Case Handling
- **Backend Connection Failure**: Settings dialog shows clear error state, app continues using local storage until connection succeeds
- **API URL Misconfiguration**: Test connection button validates endpoint before saving, prevents breaking changes
- **Backend Switch During Session**: User warned to reload page after changing backend mode to prevent data inconsistencies, visual indicator shows current backend mode in header
- **No Stock Available**: Products with zero stock appear grayed out with "Out of Stock" badge, cannot be added to orders
- **Insufficient Stock**: Order creation shows specific error message naming the product and available quantity
- **Empty States**: New profiles show helpful message with "Add Product" button, empty order list prompts to create first order, dashboard shows zeros gracefully
- **Invalid Profile**: Attempting to create order without profile shows validation error before form submission
- **Concurrent Orders**: Stock checks happen at order creation time to prevent race conditions from multiple users
- **Decimal Quantities**: System only accepts whole number quantities for products
- **Missing Data**: Required fields validated with clear error messages before submission
- **Export Empty Data**: Export button disabled when no data available, shows helpful message if attempted
- **Keyboard Shortcut Conflicts**: Shortcuts designed to not conflict with browser defaults, help accessible via Shift+?

## Design Direction
The design should feel professional and efficient like business software, with a clean dashboard aesthetic that prioritizes data clarity and quick task completion - minimal interface with information density balanced by generous spacing around key actions.

## Color Selection
Analogous color scheme using blues and teals to convey professionalism, trust, and clarity - perfect for business/inventory management context.

- **Primary Color**: Deep Professional Blue (oklch(0.45 0.12 250)) - Communicates reliability and corporate professionalism, used for primary actions and headers
- **Secondary Colors**: 
  - Light Blue Background (oklch(0.97 0.01 250)) - Subtle, clean backdrop that doesn't compete with content
  - Medium Teal Accent (oklch(0.55 0.10 200)) - Supporting color for secondary buttons and highlights
- **Accent Color**: Vibrant Teal (oklch(0.60 0.15 195)) - Draws attention to important elements like stock badges and active filters
- **Foreground/Background Pairings**:
  - Background (Light Blue #F7F9FB): Dark Gray text (#1E293B) - Ratio 12.8:1 ✓
  - Card (White #FFFFFF): Dark Gray text (#1E293B) - Ratio 14.5:1 ✓
  - Primary (Deep Blue #2563EB): White text (#FFFFFF) - Ratio 8.2:1 ✓
  - Secondary (Light Blue #F1F5F9): Dark Blue text (#1E3A8A) - Ratio 10.1:1 ✓
  - Accent (Vibrant Teal #14B8A6): White text (#FFFFFF) - Ratio 4.7:1 ✓
  - Muted (Pale Gray #F8FAFC): Medium Gray text (#64748B) - Ratio 5.2:1 ✓

## Font Selection
Typography should be clean, modern, and highly legible for scanning data tables and forms - using Inter for its excellent readability at all sizes and professional appearance.

- **Typographic Hierarchy**: 
  - H1 (Page Titles): Inter SemiBold/32px/tight letter spacing/-0.02em
  - H2 (Section Headers): Inter SemiBold/24px/normal letter spacing/-0.01em  
  - H3 (Card Titles): Inter Medium/18px/normal letter spacing/0
  - Body (Content): Inter Regular/14px/relaxed line height/1.6
  - Small (Meta Info): Inter Regular/12px/normal letter spacing/0.5px color muted
  - Labels (Form Fields): Inter Medium/13px/tracking-wide/uppercase

## Animations
Animations should be subtle and functional, reinforcing state changes and guiding attention without slowing down task completion - quick transitions that feel responsive rather than showy.

- **Purposeful Meaning**: Smooth page transitions convey navigation context, stock badge pulses draw attention to low inventory, success states use gentle scale animations to confirm actions
- **Hierarchy of Movement**: Primary actions (order creation) get satisfying confirmation animations, secondary interactions (hovering, selecting) use minimal 100ms fades, data updates use subtle opacity transitions

## Component Selection
- **Components**: 
  - Card (product display, order summaries, profile cards) - with subtle border and shadow on hover
  - Table (order history, product lists) - with striped rows and sticky headers
  - Dialog (order creation form, product forms, profile creation) - modal overlay with form validation
  - Select (profile picker, status filters) - with search capability for many profiles
  - Input (search, customer details) - with clear icons and validation states
  - Badge (stock status, order status, category, profile status) - color-coded by state
  - Button (primary actions) - with loading states during submission
  - Tabs (switch between Products/Orders/Profiles) - with active indicator
  - Toast (success/error notifications) - using sonner for order confirmations
  
- **Customizations**: 
  - Custom stock level indicator component with color thresholds (red <5, yellow <20, green ≥20)
  - Product card with prominent image placeholder, quick-add button, and stock badge overlay
  - Order item selector with inline quantity spinner and live subtotal
  - Profile card with statistics showing product and order counts
  
- **States**: 
  - Buttons: Default/Hover (darker)/Active (scale 0.98)/Disabled (50% opacity)
  - Inputs: Rest (border-input)/Focus (ring-2 ring-primary)/Error (border-destructive)/Success (border-accent)
  - Product Cards: Available (full opacity)/Low Stock (amber border)/Out of Stock (grayscale filter)
  
- **Icon Selection**: 
  - MagnifyingGlass (search), 
  - Package (products), 
  - ShoppingCart (orders), 
  - Storefront (profiles),
  - Gear (settings),
  - CloudArrowUp (API connected),
  - CloudSlash (API disconnected),
  - Database (local storage),
  - Plus (add actions), 
  - Check (confirmations), 
  - Warning (stock alerts),
  - Phone (mobile category),
  - Plugs (accessories category),
  - PencilSimple (edit),
  - Power (activate/deactivate)
  
- **Spacing**: 
  - Card padding: p-6
  - Section gaps: gap-8
  - Form fields: gap-4
  - Button padding: px-6 py-2.5
  - Page margins: max-w-7xl mx-auto px-4
  
- **Mobile**: 
  - Stack cards vertically on mobile, grid on desktop (grid-cols-1 md:grid-cols-2 lg:grid-cols-3)
  - Dialog forms scroll with sticky footer buttons
  - Table switches to stacked card view on mobile
  - Navigation tabs become horizontal scroll on mobile
  - Search and filters collapse into drawer on mobile
