import React, { useState, useEffect } from 'react';
import { analyticsAPI, detectionAPI, systemAPI } from '../services/api';
import { Video, Users, AlertTriangle, CheckCircle, Clock, Camera } from 'lucide-react';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useWebSocket } from '../hooks/useWebSocket';
import { formatTimestamp } from '../utils/formatTime';

const DashboardPage = () => {
  const [stats, setStats] = useState(null);
  const [recentDetections, setRecentDetections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [health, setHealth] = useState(null);

  // Listen for real-time detections
  useWebSocket('new_detection', (data) => {
    console.log('New detection received:', data);
    // Reload stats and detections when new detection arrives
    loadStats();
    loadRecentDetections();
  });

  // Listen for deletion events
  useWebSocket('detection_deleted', (data) => {
    console.log('Detection deleted:', data);
    // Reload stats and detections when detection is deleted
    loadStats();
    loadRecentDetections();
  });

  useEffect(() => {
    loadStats();
    loadRecentDetections();
    loadHealth();

    // Refresh health every 60 seconds
    const healthInterval = setInterval(loadHealth, 60000);
    return () => clearInterval(healthInterval);
  }, []);

  const loadStats = async () => {
    try {
      const response = await analyticsAPI.getDashboardStats();
      setStats(response.data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadRecentDetections = async () => {
    try {
      const response = await detectionAPI.getAll({ limit: 5 });
      setRecentDetections(response.data || []);
    } catch (error) {
      console.error('Failed to load recent detections:', error);
    }
  };

  const loadHealth = async () => {
    try {
      const response = await systemAPI.getHealth();
      setHealth(response.data);
    } catch (error) {
      console.error('Failed to load health:', error);
      setHealth({ status: 'unreachable', services: {} });
    }
  };

  const getTypeColor = (type) => {
    const colors = {
      'face_detection': 'bg-blue-100 text-blue-800',
      'face_match': 'bg-red-100 text-red-800',
      'watchlist_match': 'bg-red-100 text-red-800',
      'emotion': 'bg-purple-100 text-purple-800',
      'suspicious_behavior': 'bg-orange-100 text-orange-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  /**
   * Map a service health status string to a color + label for the UI.
   */
  const getHealthIndicator = (status) => {
    if (!status) return { color: 'bg-gray-400', label: 'Unknown' };

    const s = status.toLowerCase();
    if (s === 'healthy' || s === 'available' || s === 'connected')
      return { color: 'bg-green-500', label: status.charAt(0).toUpperCase() + status.slice(1) };
    if (s === 'mock_mode')
      return { color: 'bg-yellow-500', label: 'Mock Mode' };
    if (s.startsWith('unhealthy') || s === 'unavailable' || s === 'unreachable')
      return { color: 'bg-red-500', label: status.charAt(0).toUpperCase() + status.slice(1) };

    return { color: 'bg-gray-400', label: status };
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  const statCards = [
    {
      title: 'Active Cameras',
      value: `${stats?.active_cameras || 0} / ${stats?.total_cameras || 0}`,
      icon: Video,
      color: 'blue'
    },
    {
      title: 'Detections (24h)',
      value: stats?.detections_24h || 0,
      icon: AlertTriangle,
      color: 'yellow'
    },
    {
      title: 'Watchlist Persons',
      value: stats?.watchlist_persons || 0,
      icon: Users,
      color: 'purple'
    },
    {
      title: 'Verified Detections',
      value: (stats?.total_detections || 0) - (stats?.unverified_detections || 0),
      icon: CheckCircle,
      color: 'green'
    }
  ];

  // Build health service list from the /health endpoint response
  const healthServices = health?.services
    ? Object.entries(health.services).map(([name, status]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      ...getHealthIndicator(status),
    }))
    : [
      { name: 'Database', ...getHealthIndicator(null) },
      { name: 'Blockchain', ...getHealthIndicator(null) },
      { name: 'IPFS', ...getHealthIndicator(null) },
    ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((card, index) => {
          const Icon = card.icon;
          const colorClasses = {
            blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
            yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600',
            purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600',
            green: 'bg-green-100 dark:bg-green-900/30 text-green-600'
          };

          return (
            <div key={index} className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-gray-500 text-sm font-medium">{card.title}</h3>
                <div className={`p-2 rounded-lg ${colorClasses[card.color]}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-800">{card.value}</p>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Detections - Now Dynamic */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Recent Detections</h2>
          {recentDetections.length > 0 ? (
            <div className="space-y-3">
              {recentDetections.map((detection) => (
                <div
                  key={detection.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                      <Camera className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        Camera {detection.camera_id}
                      </p>
                      <p className="text-xs text-gray-500 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTimestamp(detection.timestamp)}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getTypeColor(detection.detection_type)}`}>
                    {detection.detection_type?.replace('_', ' ') || 'Detection'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <AlertTriangle className="h-10 w-10 mx-auto mb-2 text-gray-300" />
              <p>No recent detections</p>
              <p className="text-xs mt-1">Detections will appear here when cameras detect faces</p>
            </div>
          )}
        </div>

        {/* System Health — now DYNAMIC from /health API */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">System Health</h2>
          <div className="space-y-4">
            {healthServices.map((svc) => (
              <div key={svc.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-600">{svc.name}</span>
                <span className="text-sm font-medium flex items-center">
                  <div className={`h-2 w-2 ${svc.color} rounded-full mr-2`}></div>
                  {svc.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;