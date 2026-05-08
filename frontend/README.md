# FinDoc Intelligence Frontend

React frontend application for the FinDoc Intelligence financial Q&A system.

## Tech Stack

- **React 19.2.5** - UI framework
- **Vite 8.0.10** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Axios** - HTTP client for API communication

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components (QueryInput, AnswerDisplay, etc.)
│   ├── hooks/          # Custom React hooks (useQuery, useSession)
│   ├── services/       # API service layer
│   ├── App.jsx         # Main application component
│   ├── main.jsx        # Application entry point
│   └── index.css       # Global styles with Tailwind directives
├── public/             # Static assets
├── tailwind.config.js  # Tailwind CSS configuration
├── postcss.config.js   # PostCSS configuration
├── vite.config.js      # Vite configuration
└── package.json        # Dependencies and scripts
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173/`

### Build

Build for production:

```bash
npm run build
```

The built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Configuration

### Tailwind CSS

Tailwind CSS is configured in `tailwind.config.js` with content paths set to scan all JSX/TSX files in the `src/` directory.

The following Tailwind directives are included in `src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### Vite

Vite is configured with the React plugin in `vite.config.js`.

## Supported Models

The frontend supports multi-model comparisons by allowing users to toggle the following LLMs:
- **Llama 3.3 70B Versatile** (via Groq)
- **Llama 4 Scout 17B** (via Groq)
- **Gemini 2.5 Flash** (via Google AI Studio)

## API Integration

The frontend communicates with the FastAPI backend running on `http://localhost:8000`. The API service layer (`src/services/api.js`) uses Axios with error interceptors to normalize backend responses and handle connection issues gracefully.
