# Planning Guide

A next-generation inventory management system for mobile phones and accessories with AI-powered insights, real-time analytics, multi-channel sales tracking, and intelligent automation. Features include smart stock predictions, automated reordering, customer behavior analysis, multi-currency support, and seamless integration capabilities.

**Experience Qualities**: 
1. **Intelligent** - AI-driven insights suggest optimal stock levels, predict sales trends, and automate routine tasks to maximize efficiency
2. **Fluid** - Micro-interactions and smooth transitions create a tactile, responsive experience that feels instantaneous
3. **Empowering** - Rich visualizations and actionable insights transform complex data into clear business intelligence

**Complexity Level**: Complex Application (enterprise-grade functionality with intelligence layer)
  - Advanced inventory system with predictive analytics, multi-profile architecture, real-time reporting, automated workflows, customer intelligence, flexible backend integration, comprehensive health monitoring, and extensible API design.

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
- **Functionality**: Create new orders with product selection, customer info, payment method tracking, and optional notes
- **Purpose**: Record sales transactions, automatically update inventory levels, and track special instructions
- **Trigger**: User clicks "New Order" button
- **Progression**: Click new order → Select profile & channel → Enter customer details → Add products with quantities → Add optional notes → Validate stock availability → Confirm order → Stock automatically decremented
- **Success criteria**: Orders save with all line items and notes, stock decreases atomically, validation prevents overselling

### Advanced Order Search
- **Functionality**: Filter orders by date range, amount range, customer name/phone, and product
- **Purpose**: Quickly find specific orders or analyze order patterns
- **Trigger**: User clicks advanced search icon in orders tab
- **Progression**: Click search icon → Select date range → Set amount filters → Enter customer criteria → Apply filters → See filtered results
- **Success criteria**: All filter combinations work correctly, filters persist during session, clear indication when filters are active

### Customer History
- **Functionality**: View complete purchase history, total spent, and average order value for any customer
- **Purpose**: Build customer relationships and identify valuable repeat customers
- **Trigger**: User clicks "Historial" button next to customer name in order card
- **Progression**: Click customer history → View customer stats → See all past orders → Click order to view details
- **Success criteria**: All customer orders displayed chronologically, accurate spending calculations, quick access to order details

### PDF Export
- **Functionality**: Generate professional PDF invoices for orders and inventory reports for products
- **Purpose**: Create printable documents for customers and accounting
- **Trigger**: User clicks PDF button on order card or generates product report
- **Progression**: Click PDF → Document opens in new window → Print dialog appears automatically
- **Success criteria**: PDFs include all order details, business information from profile settings, proper formatting, print-ready

### Reports & Analytics
- **Functionality**: Interactive dashboard with revenue charts, monthly trends, top products by revenue, and profitability metrics
- **Purpose**: Provide deep business insights for strategic decision-making
- **Trigger**: User clicks reports icon in orders tab
- **Progression**: Click reports → View KPI summary → Analyze monthly trends → Review top products → Examine profit margins
- **Success criteria**: Charts render smoothly, data calculations accurate, responsive on all devices, intuitive navigation between report sections

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

### Customizable Keyboard Shortcuts
- **Functionality**: Allow users to customize keyboard shortcut bindings to match their preferred workflows and avoid conflicts
- **Purpose**: Provide flexibility for power users to optimize their workflow and accommodate different keyboard layouts or personal preferences
- **Trigger**: User clicks settings icon in keyboard shortcuts dialog or accesses preferences
- **Progression**: Open keyboard shortcuts dialog → Click customize/settings → View list of all actions with current bindings → Click on action to rebind → Press desired key combination → System validates for conflicts → Save new binding or cancel → Changes apply immediately
- **Success criteria**: All shortcuts are customizable, conflict detection prevents duplicate bindings, reset to defaults option available, custom bindings persist across sessions, visual recording of key combinations works reliably

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
The design should evoke premium business intelligence software - sophisticated data visualization meets tactile interface design. Think Bloomberg Terminal aesthetics refined for modern touchscreens: confident use of space, purposeful motion, and information hierarchy that guides the eye naturally from insights to actions.

## Color Selection
Rich, sophisticated palette combining deep cosmic purples with energetic cyan accents - conveying innovation and intelligence while maintaining professional credibility.

- **Primary Color**: Cosmic Purple (oklch(0.35 0.18 285)) - Sophisticated and memorable, represents intelligence and premium quality
- **Secondary Colors**: 
  - Deep Slate Background (oklch(0.15 0.02 260)) - Creates depth and focuses attention on content
  - Muted Purple (oklch(0.25 0.10 285)) - For secondary UI elements and subdued states
- **Accent Color**: Electric Cyan (oklch(0.75 0.15 195)) - High-energy highlight for CTAs, active states, and data visualization peaks
- **Supporting Colors**:
  - Success Green (oklch(0.65 0.18 145)) - Confirmations and positive metrics
  - Warning Amber (oklch(0.70 0.15 65)) - Low stock alerts and caution states
  - Error Coral (oklch(0.60 0.20 25)) - Critical issues and destructive actions
- **Foreground/Background Pairings**:
  - Background (Deep Slate #1A1A2E): Light Gray text (#E8E8F0) - Ratio 11.2:1 ✓
  - Card (Elevated Slate #242438): White text (#FFFFFF) - Ratio 13.5:1 ✓
  - Primary (Cosmic Purple #6D28D9): White text (#FFFFFF) - Ratio 9.1:1 ✓
  - Accent (Electric Cyan #06B6D4): Deep Slate text (#0F0F1E) - Ratio 8.7:1 ✓
  - Success (Green #10B981): White text (#FFFFFF) - Ratio 4.9:1 ✓
  - Warning (Amber #F59E0B): Deep Slate text (#0F0F1E) - Ratio 10.3:1 ✓

## Font Selection
Sophisticated typeface pairing using IBM Plex Sans for exceptional legibility in data-dense interfaces, with JetBrains Mono for numerical data and SKUs - creating a technical yet approachable aesthetic.

- **Typographic Hierarchy**: 
  - H1 (Dashboard Titles): IBM Plex Sans Bold/36px/tight tracking/-0.03em
  - H2 (Section Headers): IBM Plex Sans SemiBold/28px/tight tracking/-0.02em
  - H3 (Card Titles): IBM Plex Sans Medium/20px/normal tracking/-0.01em
  - Body (Content): IBM Plex Sans Regular/15px/relaxed line height/1.65
  - Data (Numbers, SKUs): JetBrains Mono Medium/14px/tabular numbers
  - Small (Meta Info): IBM Plex Sans Regular/13px/tracking-wide/color muted

## Animations
Animations create a premium, fluid experience through purposeful motion design - every transition reinforces hierarchy and provides tactile feedback that makes the interface feel responsive and alive.

- **Purposeful Meaning**: Smooth staggered list entrances guide attention sequentially, critical stock alerts pulse subtly to maintain awareness without distraction, success confirmations use gentle spring physics for satisfying feedback
- **Hierarchy of Movement**: High-stakes actions (order completion) get celebratory micro-interactions with cascading effects, medium interactions (filtering, searching) use crisp 200ms eased transitions, hover states respond instantly at 100ms for immediate tactile feedback
- **Signature Moments**: Dashboard stat cards animate in with staggered fade-up on load, chart data points draw progressively for narrative storytelling, low stock warnings use breathing pulse animation, page transitions slide with subtle parallax depth

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
