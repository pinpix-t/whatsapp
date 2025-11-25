/**
 * Stage Transition Chart Component
 * Shows stage transitions and common paths
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

export function TransitionsPerStageChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || !data.transitions_per_stage || data.transitions_per_stage.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No transition data available</div>
      </div>
    );
  }

  const chartData = data.transitions_per_stage.map((item) => ({
    state: item.state || 'Unknown',
    transitions: item.transition_count || 0,
    avgDuration: item.avg_duration_seconds
      ? Math.round(item.avg_duration_seconds)
      : null,
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Transitions per Stage</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="state" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip
            formatter={(value, name) => {
              if (name === 'transitions') return [value, 'Transitions'];
              if (name === 'avgDuration') return [`${value}s`, 'Avg Duration'];
              return value;
            }}
          />
          <Legend />
          <Bar yAxisId="left" dataKey="transitions" fill="#4ECDC4" name="Transitions" />
          <Bar
            yAxisId="right"
            dataKey="avgDuration"
            fill="#45B7D1"
            name="Avg Duration (seconds)"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CommonPathsChart({ data, loading }) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">Loading chart data...</div>
      </div>
    );
  }

  if (!data || !data.common_paths || data.common_paths.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 h-80 flex items-center justify-center">
        <div className="text-gray-500">No path data available</div>
      </div>
    );
  }

  const chartData = data.common_paths.slice(0, 15).map((path) => ({
    path: `${path.from_state || 'Start'} → ${path.to_state || 'End'}`,
    count: path.count || 0,
  }));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Most Common Transition Paths</h3>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={chartData} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" />
          <YAxis dataKey="path" type="category" width={200} />
          <Tooltip />
          <Legend />
          <Bar dataKey="count" fill="#98D8C8" name="Transition Count" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}



