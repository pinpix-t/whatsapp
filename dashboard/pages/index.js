/**
 * Main Dashboard Page
 * Integrates all components to display bulk quote analytics
 */

import { useState, useEffect } from 'react';
import Head from 'next/head';
import MetricsCards from '../components/MetricsCards';
import DateRangePicker from '../components/DateRangePicker';
import QuotesTable from '../components/QuotesTable';
import AbandonmentsTable from '../components/AbandonmentsTable';
import StageTransitionsTable from '../components/StageTransitionsTable';
import {
  QuotesOverTimeChart,
  RevenueOverTimeChart,
  QuotesByProductChart,
  QuantityDistributionChart,
  DiscountDistributionChart,
} from '../components/Charts';
import {
  AbandonmentsByStateChart,
  AbandonmentDistributionChart,
  AbandonmentsOverTimeChart,
} from '../components/AbandonmentChart';
import {
  FunnelChart,
  DropOffRatesChart,
} from '../components/FunnelChart';
import {
  TransitionsPerStageChart,
  CommonPathsChart,
} from '../components/StageTransitionChart';
import {
  TimePerStageChart,
  DropOffTimeChart,
} from '../components/TimeAnalysisChart';
import {
  getQuotes,
  getStats,
  getProducts,
  getTimeline,
  getAbandonments,
  getAbandonmentStats,
  getStageTransitions,
  getStageTransitionStats,
  getFunnel,
  getFunnelDetailed,
} from '../lib/api';

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [quotes, setQuotes] = useState([]);
  const [products, setProducts] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [abandonments, setAbandonments] = useState([]);
  const [abandonmentStats, setAbandonmentStats] = useState(null);
  const [transitions, setTransitions] = useState([]);
  const [transitionStats, setTransitionStats] = useState(null);
  const [funnelData, setFunnelData] = useState(null);
  const [funnelDetailed, setFunnelDetailed] = useState(null);
  const [dateRange, setDateRange] = useState({ startDate: '', endDate: '' });
  const [activeTab, setActiveTab] = useState('quotes');

  // Set default date range (last 30 days)
  useEffect(() => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);

    const defaultStartDate = startDate.toISOString().split('T')[0];
    const defaultEndDate = endDate.toISOString().split('T')[0];

    setDateRange({
      startDate: defaultStartDate,
      endDate: defaultEndDate,
    });
  }, []);

  // Fetch data when date range changes
  useEffect(() => {
    if (!dateRange.startDate || !dateRange.endDate) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const params = {
          start_date: dateRange.startDate,
          end_date: dateRange.endDate,
        };

        // Fetch all data in parallel with individual error handling
        const endpoints = [
          { name: 'stats', fn: () => getStats(params) },
          { name: 'quotes', fn: () => getQuotes({ ...params, limit: 1000 }) },
          { name: 'products', fn: () => getProducts(params) },
          { name: 'timeline', fn: () => getTimeline(params) },
          { name: 'abandonments', fn: () => getAbandonments({ ...params, limit: 1000 }) },
          { name: 'abandonmentStats', fn: () => getAbandonmentStats(params) },
          { name: 'transitions', fn: () => getStageTransitions({ ...params, limit: 1000 }) },
          { name: 'transitionStats', fn: () => getStageTransitionStats(params) },
          { name: 'funnel', fn: () => getFunnel(params) },
          { name: 'funnelDetailed', fn: () => getFunnelDetailed(params) },
        ];

        const results = await Promise.allSettled(
          endpoints.map(endpoint => endpoint.fn())
        );

        // Process results and log errors
        const [
          statsResult,
          quotesResult,
          productsResult,
          timelineResult,
          abandonmentsResult,
          abandonmentStatsResult,
          transitionsResult,
          transitionStatsResult,
          funnelResult,
          funnelDetailedResult,
        ] = results;

        // Helper to extract data or log error
        const getData = (result, endpointName, defaultValue = null) => {
          if (result.status === 'fulfilled') {
            return result.value;
          } else {
            console.error(`❌ Error fetching ${endpointName}:`, result.reason);
            if (result.reason?.response) {
              console.error(`   Status: ${result.reason.response.status}`);
              console.error(`   Data:`, result.reason.response.data);
            } else {
              console.error(`   Message:`, result.reason?.message || result.reason);
            }
            return defaultValue;
          }
        };

        const statsData = getData(statsResult, 'stats', null);
        const quotesData = getData(quotesResult, 'quotes', { quotes: [] });
        const productsData = getData(productsResult, 'products', { products: [] });
        const timelineData = getData(timelineResult, 'timeline', { timeline: [] });
        const abandonmentsData = getData(abandonmentsResult, 'abandonments', { abandonments: [] });
        const abandonmentStatsData = getData(abandonmentStatsResult, 'abandonmentStats', null);
        const transitionsData = getData(transitionsResult, 'transitions', { transitions: [] });
        const transitionStatsData = getData(transitionStatsResult, 'transitionStats', null);
        const funnelDataResult = getData(funnelResult, 'funnel', null);
        const funnelDetailedData = getData(funnelDetailedResult, 'funnelDetailed', null);

        setStats(statsData);
        setQuotes(quotesData?.quotes || []);
        setProducts(productsData?.products || []);
        setTimeline(timelineData?.timeline || []);
        setAbandonments(abandonmentsData?.abandonments || []);
        setAbandonmentStats(abandonmentStatsData);
        setTransitions(transitionsData?.transitions || []);
        setTransitionStats(transitionStatsData);
        setFunnelData(funnelDataResult);
        setFunnelDetailed(funnelDetailedData);
      } catch (error) {
        console.error('Unexpected error fetching dashboard data:', error);
        // Set empty states on error
        setStats(null);
        setQuotes([]);
        setProducts([]);
        setTimeline([]);
        setAbandonments([]);
        setAbandonmentStats(null);
        setTransitions([]);
        setTransitionStats(null);
        setFunnelData(null);
        setFunnelDetailed(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [dateRange]);

  const handleDateChange = (newDateRange) => {
    setDateRange(newDateRange);
  };

  const handleExportCSV = () => {
    if (!quotes || quotes.length === 0) {
      alert('No data to export');
      return;
    }

    // Create CSV content
    const headers = [
      'Date',
      'Product',
      'Quantity',
      'Total Price',
      'Discount %',
      'Email',
      'Postcode',
      'Offer Type',
    ];
    const rows = quotes.map((quote) => [
      new Date(quote.created_at).toLocaleDateString('en-GB'),
      quote.product || 'Unknown',
      quote.quantity || 0,
      quote.total_price || 0,
      quote.discount_percent || '',
      quote.email || '',
      quote.postcode || '',
      quote.offer_type || '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n');

    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bulk_quotes_${dateRange.startDate}_${dateRange.endDate}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <>
      <Head>
        <title>Bulk Quote Analytics Dashboard</title>
        <meta name="description" content="Analytics dashboard for bulk quote events" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold text-gray-900">
                📊 Bulk Quote Analytics
              </h1>
              <button
                onClick={handleExportCSV}
                disabled={loading || !quotes || quotes.length === 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                📥 Export CSV
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Date Range Picker */}
          <DateRangePicker
            onDateChange={handleDateChange}
            defaultStartDate={dateRange.startDate}
            defaultEndDate={dateRange.endDate}
          />

          {/* Metrics Cards */}
          <MetricsCards
            stats={stats}
            abandonmentStats={abandonmentStats}
            funnelData={funnelData}
            loading={loading}
          />

          {/* Tabs for different views */}
          <div className="mb-6 border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {[
                { id: 'quotes', label: '📊 Quotes' },
                { id: 'funnel', label: '🔽 Funnel Analysis' },
                { id: 'abandonments', label: '⚠️ Abandonments' },
                { id: 'transitions', label: '🔄 Stage Transitions' },
                { id: 'time', label: '⏱️ Time Analysis' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Quotes Tab */}
          {activeTab === 'quotes' && (
            <>
              {/* Charts Row 1 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <QuotesOverTimeChart data={timeline} loading={loading} />
                <QuotesByProductChart data={products} loading={loading} />
              </div>

              {/* Charts Row 2 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <RevenueOverTimeChart data={timeline} loading={loading} />
                <QuantityDistributionChart data={quotes} loading={loading} />
              </div>

              {/* Charts Row 3 */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <DiscountDistributionChart data={quotes} loading={loading} />
              </div>

              {/* Quotes Table */}
              <QuotesTable quotes={quotes} loading={loading} />
            </>
          )}

          {/* Funnel Tab */}
          {activeTab === 'funnel' && (
            <>
              <div className="grid grid-cols-1 gap-6 mb-6">
                <FunnelChart data={funnelData} loading={loading} />
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <DropOffRatesChart data={funnelData} loading={loading} />
              </div>
            </>
          )}

          {/* Abandonments Tab */}
          {activeTab === 'abandonments' && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <AbandonmentsByStateChart
                  data={abandonmentStats?.abandonments_by_state || []}
                  loading={loading}
                />
                <AbandonmentDistributionChart
                  data={abandonmentStats?.abandonments_by_state || []}
                  loading={loading}
                />
              </div>
              <div className="grid grid-cols-1 gap-6 mb-6">
                <AbandonmentsOverTimeChart data={abandonments} loading={loading} />
              </div>
              <AbandonmentsTable abandonments={abandonments} loading={loading} />
            </>
          )}

          {/* Stage Transitions Tab */}
          {activeTab === 'transitions' && (
            <>
              <div className="grid grid-cols-1 gap-6 mb-6">
                <TransitionsPerStageChart data={transitionStats} loading={loading} />
              </div>
              <div className="grid grid-cols-1 gap-6 mb-6">
                <CommonPathsChart data={transitionStats} loading={loading} />
              </div>
              <StageTransitionsTable transitions={transitions} loading={loading} />
            </>
          )}

          {/* Time Analysis Tab */}
          {activeTab === 'time' && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <TimePerStageChart data={funnelDetailed} loading={loading} />
                <DropOffTimeChart data={funnelDetailed} loading={loading} />
              </div>
            </>
          )}
        </main>

        {/* Footer */}
        <footer className="bg-white border-t mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <p className="text-center text-sm text-gray-500">
              Bulk Quote Analytics Dashboard - Last updated:{' '}
              {new Date().toLocaleString('en-GB')}
            </p>
          </div>
        </footer>
      </div>
    </>
  );
}

