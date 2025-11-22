/**
 * Metrics Cards Component
 * Displays key metrics in card format
 */

export default function MetricsCards({ stats, abandonmentStats, funnelData, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  const formatCurrency = (value) => {
    if (!value) return 'N/A';
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(value);
  };

  const formatNumber = (value) => {
    if (!value) return '0';
    return new Intl.NumberFormat('en-GB').format(value);
  };

  const formatPercentage = (value) => {
    if (!value && value !== 0) return 'N/A';
    return `${value.toFixed(1)}%`;
  };

  // Calculate abandonment rate
  const totalStarts = funnelData?.total_starts || 0;
  const totalAbandonments = abandonmentStats?.total_abandonments || 0;
  const abandonmentRate =
    totalStarts > 0 ? (totalAbandonments / totalStarts) * 100 : 0;

  const metrics = [
    {
      title: 'Total Quotes',
      value: formatNumber(stats?.total_quotes || 0),
      icon: '📊',
    },
    {
      title: 'Total Quantity',
      value: formatNumber(stats?.total_quantity || 0),
      icon: '📦',
    },
    {
      title: 'Total Quote Value',
      value: formatCurrency(stats?.total_revenue || 0),
      icon: '💰',
    },
    {
      title: 'Avg Quantity/Quote',
      value: stats?.avg_quantity ? stats.avg_quantity.toFixed(1) : '0',
      icon: '📈',
    },
    {
      title: 'Total Abandonments',
      value: formatNumber(totalAbandonments),
      icon: '⚠️',
    },
    {
      title: 'Abandonment Rate',
      value: formatPercentage(abandonmentRate),
      icon: '📉',
    },
    {
      title: 'Completion Rate',
      value: formatPercentage(funnelData?.completion_rate || 0),
      icon: '✅',
    },
    {
      title: 'Total Flow Starts',
      value: formatNumber(totalStarts),
      icon: '🚀',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {metrics.map((metric, index) => (
        <div
          key={index}
          className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">
                {metric.title}
              </p>
              <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
            </div>
            <div className="text-3xl">{metric.icon}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

