# Change Proposal: Dashboard & Main Interface

## Why

The Medical_KG system currently exposes a comprehensive API but lacks a user interface. Mercor analysts, engagement leads, and strategists need a visual dashboard to monitor system health, access key workflows, and navigate to specialized tools without writing API calls or scripts.

## What Changes

- Create a responsive web dashboard as the primary entry point for all Medical_KG functionality
- Implement real-time system health monitoring with service status indicators
- Add quick-access cards for primary workflows (ingestion, retrieval, extraction, briefings)
- Display activity feed showing recent operations and their status
- Integrate navigation to all specialized UI modules
- Provide user profile/session management with role-based UI customization
- Add global search bar for cross-system entity lookup
- Implement dark/light theme toggle and accessibility features (WCAG 2.1 AA)

## Impact

**Affected specs:** NEW `ui-dashboard` capability

**Affected code:**

- NEW `src/Medical_KG/ui/` directory with React/TypeScript frontend
- NEW `src/Medical_KG/ui/dashboard/` - dashboard components
- NEW `src/Medical_KG/ui/shared/` - shared UI components (layout, nav, theme)
- NEW `src/Medical_KG/api/ui_backend.py` - API endpoints for dashboard data
- MODIFIED `src/Medical_KG/app.py` - serve static UI assets
- NEW `package.json`, `tsconfig.json`, `vite.config.ts` - frontend tooling
- NEW `src/Medical_KG/ui/services/api-client.ts` - typed API client

**Technology stack:**

- Frontend: React 18+, TypeScript, Vite, TanStack Query, Recharts, Tailwind CSS
- State management: Zustand for global state, React Query for server state
- Routing: React Router v6
- Testing: Vitest, React Testing Library
- Build: Vite with backend proxy for development
