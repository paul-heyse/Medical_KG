# Implementation Tasks

## 1. Project Setup

- [ ] 1.1 Initialize Vite + React + TypeScript project in `src/Medical_KG/ui/`
- [ ] 1.2 Configure Tailwind CSS, install UI dependencies (Recharts, React Router, TanStack Query, Zustand)
- [ ] 1.3 Set up ESLint, Prettier, and Vitest for frontend code
- [ ] 1.4 Create typed API client with OpenAPI spec generation from FastAPI
- [ ] 1.5 Configure Vite proxy to backend during development

## 2. Core Layout & Navigation

- [ ] 2.1 Implement `AppShell` component (header, sidebar, main content, footer)
- [ ] 2.2 Create responsive sidebar navigation with collapsible sections
- [ ] 2.3 Build top header with global search, notifications, user menu, theme toggle
- [ ] 2.4 Implement React Router setup with protected routes
- [ ] 2.5 Create theme provider (dark/light mode with system preference detection)
- [ ] 2.6 Add loading states, error boundaries, and toast notifications

## 3. Dashboard Components

- [ ] 3.1 Create `HealthStatusCard` showing API health, service status, and latency
- [ ] 3.2 Build `ActivityFeed` component displaying recent operations (last 50)
- [ ] 3.3 Implement `QuickActions` grid with workflow shortcuts (Ingest, Retrieve, Extract, Brief)
- [ ] 3.4 Add `SystemMetrics` charts (ingestion volume, query rate, KG node count over time)
- [ ] 3.5 Create `RecentDocuments` list with quick preview and navigation
- [ ] 3.6 Build `ActiveJobs` widget showing in-progress ingestion/extraction tasks

## 4. Backend API Endpoints

- [ ] 4.1 Add `/api/dashboard/health` endpoint returning detailed service health
- [ ] 4.2 Implement `/api/dashboard/activity` with paginated activity feed
- [ ] 4.3 Create `/api/dashboard/metrics` returning time-series system metrics
- [ ] 4.4 Add `/api/dashboard/recent-documents` for latest ingested documents
- [ ] 4.5 Implement `/api/dashboard/active-jobs` for in-progress operations
- [ ] 4.6 Add WebSocket endpoint `/ws/dashboard` for real-time updates

## 5. Testing & Documentation

- [ ] 5.1 Write unit tests for dashboard components (80%+ coverage)
- [ ] 5.2 Add integration tests for dashboard API endpoints
- [ ] 5.3 Create Storybook stories for UI components
- [ ] 5.4 Document setup, development, and build process in `docs/ui_development.md`
- [ ] 5.5 Add E2E tests for critical dashboard flows (Playwright)
