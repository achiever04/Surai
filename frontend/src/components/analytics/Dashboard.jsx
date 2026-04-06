import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Dashboard = ({ stats }) => {
  if (!stats) {
    return <div>Loading statistics...</div>;
  }

  const chartData = stats.daily_detections?.map(d => ({
    date: new Date(d.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
    detections: d.count
  })) || [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Cameras"
          value={stats.total_cameras}
          subtitle={`${stats.active_cameras} active`}
          color="blue"
        />
        <StatCard
          title="Detections (24h)"
          value={stats.detections_24h}
          subtitle="Last 24 hours"
          color="yellow"
        />
        <StatCard
          title="Watchlist"
          value={stats.watchlist_persons}
          subtitle="Active persons"
          color="purple"
        />
        <StatCard
          title="Verified"
          value={stats.verified_detections || 0}
          subtitle="Confirmed detections"
          color="green"
        />
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-bold mb-4">Detection Trends (Last 7 Days)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="detections" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-4">Detection by Type</h3>
          <div className="space-y-3">
            {stats.by_type && Object.entries(stats.by_type).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <span className="text-gray-700 capitalize">{type.replace('_', ' ')}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-4">System Health</h3>
          <div className="space-y-3">
            <HealthItem label="Database" status="healthy" />
            <HealthItem label="Blockchain" status="healthy" />
            <HealthItem label="IPFS" status="healthy" />
            <HealthItem label="AI Engine" status="healthy" />
          </div>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, subtitle, color }) => {
  const colors = {
    blue: 'bg-blue-100 text-blue-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    purple: 'bg-purple-100 text-purple-600',
    green: 'bg-green-100 text-green-600'
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="text-sm text-gray-500 mb-1">{title}</div>
      <div className={`text-3xl font-bold ${colors[color]}`}>{value}</div>
      <div className="text-xs text-gray-400 mt-1">{subtitle}</div>
    </div>
  );
};

const HealthItem = ({ label, status }) => (
  <div className="flex items-center justify-between">
    <span className="text-gray-700">{label}</span>
    <span className={`px-2 py-1 text-xs rounded-full ${
      status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
    }`}>
      {status === 'healthy' ? '● Healthy' : '● Down'}
    </span>
  </div>
);

export default Dashboard;