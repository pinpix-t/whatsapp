# Bulk Quote Analytics Dashboard

A modern Next.js dashboard for visualizing bulk quote events from the WhatsApp bot analytics system.

## Features

- **Key Metrics**: Total quotes, quantity, revenue, and averages
- **Interactive Charts**: 
  - Quotes over time (line chart)
  - Revenue over time (bar chart)
  - Quotes by product (pie chart)
  - Quantity distribution (histogram)
  - Discount distribution (histogram)
- **Data Table**: Sortable, paginated table with all quote details
- **Date Filtering**: Filter data by custom date ranges
- **CSV Export**: Export filtered data to CSV
- **Responsive Design**: Works on mobile, tablet, and desktop

## Setup

### Prerequisites

- Node.js 18+ and npm/yarn
- FastAPI backend running with analytics endpoints

### Installation

1. Navigate to the dashboard directory:
```bash
cd dashboard
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Create environment file:
```bash
cp .env.local.example .env.local
```

4. Update `.env.local` with your FastAPI backend URL:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
# For production, use your Railway deployment URL:
# NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

### Development

Run the development server:

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

Build for production:

```bash
npm run build
npm start
```

## Deployment to Vercel

1. Push your code to GitHub
2. Go to [Vercel](https://vercel.com) and import your repository
3. Set the following environment variable:
   - `NEXT_PUBLIC_API_URL`: Your FastAPI backend URL (e.g., `https://your-app.railway.app`)
4. Deploy!

Vercel will automatically deploy on every push to your main branch.

## API Endpoints

The dashboard expects the following FastAPI endpoints to be available:

- `GET /api/analytics/quotes` - Get bulk quotes with filtering
- `GET /api/analytics/stats` - Get aggregated statistics
- `GET /api/analytics/products` - Get quotes grouped by product
- `GET /api/analytics/timeline` - Get quotes over time

See `api/analytics.py` in the main project for endpoint documentation.

## Project Structure

```
dashboard/
├── components/          # React components
│   ├── MetricsCards.js
│   ├── Charts.js
│   ├── QuotesTable.js
│   └── DateRangePicker.js
├── lib/                # Utilities
│   └── api.js          # API client
├── pages/              # Next.js pages
│   ├── _app.js
│   └── index.js        # Main dashboard page
├── styles/             # CSS files
│   └── globals.css
├── package.json
├── next.config.js
├── tailwind.config.js
└── README.md
```

## Technologies

- **Next.js 14** - React framework
- **React 18** - UI library
- **Recharts** - Charting library
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **date-fns** - Date utilities

## License

Part of the WhatsApp Bot project.

