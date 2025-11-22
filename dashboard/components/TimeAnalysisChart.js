/**
 * Time Analysis Chart Component
 * Shows time spent per stage and duration trends
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
} from 'recharts';

export function TimePerStageChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || !data.time_per_stage || data.time_per_stage.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No time data available</div>
      </div>
    );
  }

  const chartData = data.time_per_stage.map((item) => ({
    state: item.state || 'Unknown',
    avgDuration: Math.round(item.avg_duration_seconds || 0),
    transitionCount: item.transition_count || 0,
  }));

  // Format duration for display
  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}m ${secs}s`;
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Average Time Spent per Stage</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="state" />
          <YAxis />
          <Tooltip
            formatter={(value, name) => {
              if (name === 'avgDuration') return [formatDuration(value), 'Avg Duration'];
              if (name === 'transitionCount') return [value, 'Transitions'];
              return value;
            }}
          />
          <Legend />
          <Bar dataKey="avgDuration" fill="#45B7D1" name="Avg Duration (seconds)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DropOffTimeChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || !data.drop_off_points || data.drop_off_points.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No drop-off data available</div>
      </div>
    );
  }

  const chartData = data.drop_off_points.map((item) => ({
    state: item.state || 'Unknown',
    abandonments: item.abandonment_count || 0,
    avgTimeBeforeAbandonment: Math.round(
      item.avg_time_before_abandonment_seconds || 0
    ),
  }));

  // Format duration for display
  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}m ${secs}s`;
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Drop-off Points & Time Before Abandonment</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="state" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip
            formatter={(value, name) => {
              if (name === 'abandonments') return [value, 'Abandonments'];
              if (name === 'avgTimeBeforeAbandonment')
                return [formatDuration(value), 'Avg Time Before Abandonment'];
              return value;
            }}
          />
          <Legend />
          <Bar yAxisId="left" dataKey="abandonments" fill="#FF6B6B" name="Abandonments" />
          <Bar
            yAxisId="right"
            dataKey="avgTimeBeforeAbandonment"
            fill="#FFA07A"
            name="Avg Time Before Abandonment (seconds)"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

