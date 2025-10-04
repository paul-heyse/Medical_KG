# UI Dashboard Specification

## Overview

The dashboard provides the primary entry point and system overview for Medical_KG users, displaying real-time health metrics, recent activity, and quick access to all major workflows.

## ADDED Requirements

### Requirement: Responsive Layout

The dashboard SHALL render correctly on desktop (1920x1080+), laptop (1366x768+), and tablet (768x1024+) viewports with appropriate content reflow and no horizontal scrolling.

#### Scenario: Desktop layout

- **WHEN** a user views the dashboard on a desktop browser at 1920x1080
- **THEN** the sidebar SHALL remain expanded by default
- **AND** the main content SHALL display in a 3-column grid layout
- **AND** all charts and cards SHALL be visible without scrolling

#### Scenario: Tablet layout

- **WHEN** a user views the dashboard on a tablet at 768x1024
- **THEN** the sidebar SHALL collapse to icon-only mode
- **AND** the main content SHALL display in a 2-column grid layout
- **AND** cards SHALL stack vertically maintaining readability

### Requirement: Real-Time Health Monitoring

The dashboard SHALL display the current health status of all core services (retrieval, extraction, facets, KG, ingestion) with automatic refresh every 30 seconds.

#### Scenario: All services healthy

- **WHEN** all services return 200 status from `/health` endpoint
- **THEN** each service SHALL display a green indicator with "Ready" status
- **AND** overall system status SHALL show "All Systems Operational"
- **AND** average response time SHALL be displayed for each service

#### Scenario: Service degradation

- **WHEN** any service reports degraded performance or returns 5xx error
- **THEN** that service SHALL display a yellow indicator with "Degraded" status
- **AND** overall system status SHALL show "Partial Outage"
- **AND** an alert banner SHALL appear at the top of the dashboard
- **AND** affected service details SHALL be expandable

#### Scenario: Service failure

- **WHEN** any service is unreachable or returns consistent errors
- **THEN** that service SHALL display a red indicator with "Down" status
- **AND** overall system status SHALL show "Service Unavailable"
- **AND** a critical alert SHALL be displayed with troubleshooting link

### Requirement: Activity Feed

The dashboard SHALL display a real-time feed of the last 50 system operations with operation type, status, timestamp, and user attribution.

#### Scenario: Recent operations display

- **WHEN** a user views the activity feed
- **THEN** operations SHALL be displayed in reverse chronological order
- **AND** each entry SHALL show operation type icon, description, status badge, timestamp, and initiating user
- **AND** the feed SHALL auto-update via WebSocket when new operations complete
- **AND** users SHALL be able to filter by operation type (ingest, extract, retrieve, kg_write)

#### Scenario: Operation details expansion

- **WHEN** a user clicks on an activity feed entry
- **THEN** a detail panel SHALL expand showing full operation metadata
- **AND** for ingestion operations, the panel SHALL show document ID, source, and record count
- **AND** for failed operations, the panel SHALL display error messages and stack traces
- **AND** a "View Full Report" link SHALL navigate to the appropriate detail page

### Requirement: Quick Actions

The dashboard SHALL provide one-click access to initiate the four primary workflows: Ingest Document, Search/Retrieve, Extract Clinical Data, and Generate Briefing.

#### Scenario: Quick action cards

- **WHEN** a user views the dashboard
- **THEN** four prominent action cards SHALL be displayed in the upper section
- **AND** each card SHALL show an icon, title, description, and "Start" button
- **AND** clicking "Start" SHALL navigate to the appropriate workflow page

#### Scenario: Workflow shortcuts

- **WHEN** a user clicks "Ingest Document" action
- **THEN** they SHALL be directed to `/ui/ingestion` with the ingestion form pre-loaded
- **WHEN** a user clicks "Search/Retrieve" action
- **THEN** they SHALL be directed to `/ui/retrieval` with search bar focused
- **WHEN** a user clicks "Extract Clinical Data" action
- **THEN** they SHALL be directed to `/ui/extraction` with chunk selector visible
- **WHEN** a user clicks "Generate Briefing" action
- **THEN** they SHALL be directed to `/ui/briefings` with topic input ready

### Requirement: System Metrics Visualization

The dashboard SHALL display time-series charts for key system metrics: ingestion volume (last 7 days), query rate (last 24 hours), and knowledge graph growth (last 30 days).

#### Scenario: Ingestion volume chart

- **WHEN** a user views the ingestion volume chart
- **THEN** it SHALL display a bar chart with daily ingestion counts for the last 7 days
- **AND** bars SHALL be color-coded by source type (clinical trials, literature, guidelines, etc.)
- **AND** hovering over a bar SHALL show tooltip with exact counts and breakdown

#### Scenario: Query rate chart

- **WHEN** a user views the query rate chart
- **THEN** it SHALL display a line chart with hourly query counts for the last 24 hours
- **AND** the chart SHALL distinguish between successful and failed queries
- **AND** a secondary Y-axis SHALL show average latency

#### Scenario: Knowledge graph growth

- **WHEN** a user views the KG growth chart
- **THEN** it SHALL display a stacked area chart showing node counts by type (Study, Drug, Condition, etc.) over the last 30 days
- **AND** users SHALL be able to toggle node types on/off
- **AND** clicking a data point SHALL navigate to the KG explorer filtered to that date range

### Requirement: Global Search

The dashboard header SHALL include a global search bar that queries across documents, entities, and briefings with autocomplete suggestions.

#### Scenario: Search autocomplete

- **WHEN** a user types at least 3 characters in the global search bar
- **THEN** a dropdown SHALL appear with up to 10 autocomplete suggestions
- **AND** suggestions SHALL be grouped by type (Documents, Entities, Briefings)
- **AND** each suggestion SHALL show a preview (e.g., document title, entity name, briefing topic)

#### Scenario: Search execution

- **WHEN** a user presses Enter or selects a suggestion
- **THEN** they SHALL be navigated to the appropriate detail page
- **AND** for general text queries, they SHALL be directed to `/ui/retrieval` with query pre-filled
- **AND** for entity IDs (NCT*, RXCUI*, LOINC*), they SHALL go directly to the entity detail page

### Requirement: User Session Management

The dashboard SHALL display the current user's profile information, active session details, and provide logout functionality in the header menu.

#### Scenario: User menu display

- **WHEN** a user clicks their profile icon in the header
- **THEN** a dropdown menu SHALL appear showing username, email, role, and license tier
- **AND** menu options SHALL include "Profile Settings", "API Keys", "Preferences", and "Logout"

#### Scenario: Logout

- **WHEN** a user clicks "Logout"
- **THEN** their session SHALL be terminated
- **AND** they SHALL be redirected to the login page
- **AND** any cached data SHALL be cleared from local storage

### Requirement: Theme Toggle

The dashboard SHALL support both light and dark themes with user preference persistence and automatic system theme detection.

#### Scenario: Theme switching

- **WHEN** a user clicks the theme toggle button
- **THEN** the entire UI SHALL transition to the alternate theme within 200ms
- **AND** the user's preference SHALL be stored in local storage
- **AND** all charts, cards, and text SHALL adapt to the new theme with appropriate contrast

#### Scenario: System theme detection

- **WHEN** a user has no saved theme preference
- **THEN** the UI SHALL automatically match the operating system's theme preference
- **AND** the UI SHALL update if the system theme changes while the app is open

### Requirement: Accessibility

The dashboard SHALL conform to WCAG 2.1 Level AA standards with keyboard navigation, screen reader support, and appropriate ARIA labels.

#### Scenario: Keyboard navigation

- **WHEN** a user navigates the dashboard using only keyboard
- **THEN** all interactive elements SHALL be reachable via Tab key
- **AND** focus indicators SHALL be clearly visible (3px outline)
- **AND** dropdown menus SHALL open with Enter/Space and close with Escape

#### Scenario: Screen reader compatibility

- **WHEN** a screen reader user navigates the dashboard
- **THEN** all icons SHALL have aria-label attributes with descriptive text
- **AND** charts SHALL have aria-describedby attributes with data summaries
- **AND** dynamic content updates SHALL announce via aria-live regions

### Requirement: Performance

The dashboard SHALL achieve a Lighthouse performance score of 90+ with First Contentful Paint under 1.5s and Time to Interactive under 3s on a mid-range laptop.

#### Scenario: Initial load performance

- **WHEN** a user navigates to the dashboard for the first time
- **THEN** the initial HTML SHALL load within 500ms
- **AND** the First Contentful Paint SHALL occur within 1.5s
- **AND** the dashboard SHALL be fully interactive within 3s
- **AND** JavaScript bundle size SHALL not exceed 300KB gzipped

#### Scenario: Real-time updates

- **WHEN** the dashboard receives real-time updates via WebSocket
- **THEN** updates SHALL be applied to the UI within 200ms
- **AND** UI updates SHALL not cause layout shifts (CLS < 0.1)
- **AND** chart re-renders SHALL use React.memo to prevent unnecessary updates
