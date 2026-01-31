# SpotDL Frontend

React web interface for SpotDL - search, download, and manage music matches.

## Features

- **Search**: Resolve songs from any supported platform URL
- **Download Queue**: Monitor download progress with real-time updates
- **Match Voting**: Vote on match quality to improve results
- **Match Submission**: Submit user-discovered matches
- **Settings**: Configure audio format, quality, and output preferences

## Tech Stack

- React 19
- TypeScript 5.x
- Vite 6.x
- TailwindCSS 4.x
- TanStack Router (file-based routing)
- TanStack Query (data fetching)
- Zustand (state management)

## Development

### Prerequisites

- Node.js 22+
- pnpm 9+

### Setup

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Open http://localhost:5173
```

### Scripts

```bash
# Development
pnpm dev           # Start dev server
pnpm build         # Production build
pnpm preview       # Preview production build

# Testing
pnpm test          # Run unit tests
pnpm test:e2e      # Run E2E tests (Playwright)
pnpm test:e2e:ui   # Run E2E tests with UI

# Code Quality
pnpm lint          # Run ESLint
pnpm type-check    # Run TypeScript compiler
pnpm format        # Format with Prettier
```

## Project Structure

```
src/
├── api/              # TanStack Query hooks
│   ├── client.ts     # Axios instance
│   ├── auth.ts       # Authentication
│   ├── songs.ts      # Song resolution/search
│   ├── matches.ts    # Match finding/submission
│   └── votes.ts      # Voting
├── components/
│   ├── ui/           # Base UI components
│   ├── search/       # Search components
│   ├── download/     # Download queue components
│   └── auth/         # Auth forms
├── routes/           # TanStack Router pages
│   ├── index.tsx     # Home/search
│   ├── queue.tsx     # Download queue
│   ├── matching.tsx  # Match voting
│   ├── settings.tsx  # Settings
│   └── auth/         # Login/register
├── stores/           # Zustand stores
│   ├── auth.ts       # Auth state
│   ├── queue.ts      # Download queue
│   └── settings.ts   # User settings
└── types/            # TypeScript types
```

## Environment Variables

Create a `.env.local` file:

```bash
VITE_API_URL=http://localhost:8000
```

## Docker

```bash
# Build image
docker build -t spotdl-frontend .

# Run container
docker run -p 3000:80 spotdl-frontend
```

## Testing

### Unit Tests (Vitest)

```bash
# Run tests
pnpm test

# Watch mode
pnpm test --watch

# Coverage report
pnpm test --coverage
```

### E2E Tests (Playwright)

```bash
# Install browsers
pnpm exec playwright install

# Run tests
pnpm test:e2e

# Run with UI
pnpm test:e2e:ui

# Run specific test file
pnpm test:e2e e2e/home.spec.ts
```

## License

MIT
