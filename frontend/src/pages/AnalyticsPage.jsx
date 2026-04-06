import React, { useState, useEffect } from 'react';
import { analyticsAPI } from '../services/api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell
} from 'recharts';
import { TrendingUp, PieChart as PieIcon, Activity } from 'lucide-react';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useWebSocket } from '../hooks/useWebSocket';

const AnalyticsPage = () => {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(7);

  // Listen for real-time detection updates
  useWebSocket('new_detection', (data) => {
    console.log('Analytics: New detection received:', data);
    loadAnalytics();
    loadTrends();
  });

  // Listen for deletion events
  useWebSocket('detection_deleted', (data) => {
    console.log('Analytics: Detection deleted:', data);
    loadAnalytics();
    loadTrends();
  });

  useEffect(() => {
    loadAnalytics();
    loadTrends();
  }, [timeRange]);

  const loadAnalytics = async () => {
    setIsLoading(true);
    try {
      const response = await analyticsAPI.getDashboardStats();
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadTrends = async () => {
    try {
      const response = await analyticsAPI.getDetectionTrends({ days: timeRange });
      setTrends(response.data);
    } catch (error) {
      console.error('Failed to load trends:', error);
    }
  };

  if (isLoading) return <LoadingSpinner />;

  // Transform data for charts using trends data
  const chartData = trends?.daily_detections?.map(d => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    detections: d.count,
    accuracy: d.accuracy
  })) || [];

  const typeData = trends?.by_type ? Object.entries(trends.by_type).map(([name, value]) => ({
    name: name.replace('_', ' '),
    value
  })) : [];

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444'];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-800">System Analytics</h1>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(Number(e.target.value))}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 outline-none"
        >
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
          <option value={90}>Last Quarter</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trend Chart with Accuracy */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              Detection Activity & Accuracy
            </h2>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} dy={10} />
                <YAxis yAxisId="left" axisLine={false} tickLine={false} />
                <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  cursor={{ fill: '#F3F4F6' }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="detections"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  name="Detections"
                  dot={{ fill: '#3B82F6', r: 4 }}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#10B981"
                  strokeWidth={2}
                  name="Accuracy %"
                  dot={{ fill: '#10B981', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Distribution Chart */}
        <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
              <PieIcon className="w-5 h-5 text-purple-600" />
              Event Distribution
            </h2>
          </div>
          <div className="h-80 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={typeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {typeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white shadow-lg shadow-blue-200">
          <div className="text-blue-100 text-sm font-medium mb-1">Total Events</div>
          <div className="text-3xl font-bold">{stats?.total_detections || 0}</div>
          <div className="mt-2 text-xs bg-blue-400/30 inline-block px-2 py-1 rounded">
            {stats?.weekly_change_percent > 0 ? '+' : ''}{stats?.weekly_change_percent || 0}% from last week
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-500 text-sm font-medium mb-1">Peak Activity</div>
          <div className="text-3xl font-bold text-gray-800">{stats?.peak_hour || 'N/A'}</div>
          <div className="mt-2 text-xs text-green-600 font-medium">
            Busiest Hour (24h)
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
          <div className="text-gray-500 text-sm font-medium mb-1">Verification Rate</div>
          <div className="text-3xl font-bold text-gray-800">
            {stats?.total_detections > 0
              ? `${(((stats?.total_detections - stats?.unverified_detections) / stats?.total_detections) * 100).toFixed(1)}%`
              : 'N/A'
            }
          </div>
          <div className="mt-2 text-xs text-blue-600 font-medium">
            Blockchain Confirmed
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;