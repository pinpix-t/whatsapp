/**
 * Charts Component
 * Displays various charts using Recharts
 */

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export function QuotesOverTimeChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No data available</div>
      </div>
    );
  }

  // Format dates for display
  const formattedData = data.map((item) => ({
    ...item,
    date: new Date(item.date).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
    }),
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Quotes Over Time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="quote_count"
            stroke="#0088FE"
            strokeWidth={2}
            name="Quotes"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RevenueOverTimeChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No data available</div>
      </div>
    );
  }

  const formattedData = data.map((item) => ({
    ...item,
    date: new Date(item.date).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
    }),
    revenue: item.total_revenue || 0,
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Revenue Over Time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip
            formatter={(value) =>
              new Intl.NumberFormat('en-GB', {
                style: 'currency',
                currency: 'GBP',
              }).format(value)
            }
          />
          <Legend />
          <Bar dataKey="revenue" fill="#00C49F" name="Revenue (£)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function QuotesByProductChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No data available</div>
      </div>
    );
  }

  const chartData = data.map((item) => ({
    name: item.product || 'Unknown',
    value: item.quote_count || 0,
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Quotes by Product</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function QuantityDistributionChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No data available</div>
      </div>
    );
  }

  // Create bins for quantity distribution
  const bins = [0, 25, 50, 100, 200, 500, 1000, Infinity];
  const binLabels = ['0-25', '26-50', '51-100', '101-200', '201-500', '501-1000', '1000+'];
  const distribution = bins.map(() => 0);

  data.forEach((quote) => {
    const quantity = quote.quantity || 0;
    for (let i = 0; i < bins.length - 1; i++) {
      if (quantity >= bins[i] && quantity < bins[i + 1]) {
        distribution[i]++;
        break;
      }
    }
  });

  const chartData = binLabels.map((label, index) => ({
    range: label,
    count: distribution[index],
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Quantity Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="range" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="count" fill="#FF8042" name="Number of Quotes" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DiscountDistributionChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No data available</div>
      </div>
    );
  }

  // Filter out null/undefined discount values
  const discounts = data
    .map((quote) => quote.discount_percent)
    .filter((d) => d != null && !isNaN(d));

  if (discounts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No discount data available</div>
      </div>
    );
  }

  // Create bins for discount distribution
  const bins = [0, 5, 10, 15, 20, 25, 30, Infinity];
  const binLabels = ['0-5%', '6-10%', '11-15%', '16-20%', '21-25%', '26-30%', '30%+'];
  const distribution = bins.map(() => 0);

  discounts.forEach((discount) => {
    for (let i = 0; i < bins.length - 1; i++) {
      if (discount >= bins[i] && discount < bins[i + 1]) {
        distribution[i]++;
        break;
      }
    }
  });

  const chartData = binLabels.map((label, index) => ({
    range: label,
    count: distribution[index],
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Discount Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="range" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="count" fill="#FFBB28" name="Number of Quotes" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

