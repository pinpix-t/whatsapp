/**
 * Funnel Chart Component
 * Shows conversion funnel with drop-off rates
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';

export function FunnelChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading funnel data...</div>
      </div>
    );
  }

  if (!data || !data.funnel_stages || data.funnel_stages.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No funnel data available</div>
      </div>
    );
  }

  const chartData = data.funnel_stages.map((stage) => ({
    state: stage.state || 'Unknown',
    users: stage.user_count || 0,
    dropOff: stage.drop_off_rate || 0,
    conversion: stage.conversion_rate || 0,
  }));

  // Color bars based on conversion rate
  const getColor = (conversion) => {
    if (conversion >= 70) return '#4ECDC4';
    if (conversion >= 40) return '#45B7D1';
    if (conversion >= 20) return '#FFA07A';
    return '#FF6B6B';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Conversion Funnel</h3>
      <div className="mb-4 text-sm text-gray-600">
        <p>Total Starts: {data.total_starts || 0}</p>
        <p>Total Completions: {data.total_completions || 0}</p>
        <p className="font-semibold">Completion Rate: {data.completion_rate || 0}%</p>
      </div>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={chartData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis dataKey="state" type="category" width={150} />
          <Tooltip
            formatter={(value, name) => {
              if (name === 'users') return [`${value} users`, 'Users'];
              if (name === 'dropOff') return [`${value}%`, 'Drop-off Rate'];
              if (name === 'conversion') return [`${value}%`, 'Conversion Rate'];
              return value;
            }}
          />
          <Legend />
          <Bar dataKey="users" name="Users at Stage">
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getColor(entry.conversion)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-4 text-xs text-gray-500">
        <p>Hover over bars to see drop-off and conversion rates</p>
      </div>
    </div>
  );
}

export function DropOffRatesChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || !data.funnel_stages || data.funnel_stages.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No funnel data available</div>
      </div>
    );
  }

  const chartData = data.funnel_stages.map((stage) => ({
    state: stage.state || 'Unknown',
    dropOffRate: stage.drop_off_rate || 0,
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Drop-off Rates by Stage</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="state" />
          <YAxis />
          <Tooltip formatter={(value) => [`${value}%`, 'Drop-off Rate']} />
          <Legend />
          <Bar dataKey="dropOffRate" fill="#FF6B6B" name="Drop-off Rate (%)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}



