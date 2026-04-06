import React, { useState, useEffect } from 'react';
import { detectionAPI, blockchainAPI } from '../services/api';
import { Shield, Search, CheckCircle, Clock, FileText, Link as LinkIcon, XCircle, AlertTriangle } from 'lucide-react';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useWebSocket } from '../hooks/useWebSocket';
import { formatTimestamp } from '../utils/formatTime';

const AuditPage = () => {
  const [detections, setDetections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [actionInProgress, setActionInProgress] = useState(null);

  // Listen for real-time detection events
  useWebSocket('new_detection', (data) => {
    console.log('Audit: New detection event:', data);
    loadDetections();
  });

  useEffect(() => {
    loadDetections();
  }, []);

  const loadDetections = async () => {
    try {
      const response = await detectionAPI.getAll({ limit: 50 });
      setDetections(response.data);
    } catch (error) {
      console.error('Failed to load detections for audit:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async (detection) => {
    setActionInProgress(detection.id);
    try {
      await detectionAPI.verify(detection.id);
      loadDetections(); // Refresh to show updated status
    } catch (error) {
      console.error('Failed to verify detection:', error);
      alert('Failed to verify evidence. You may not have permission.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReject = async (detection) => {
    setActionInProgress(detection.id);
    try {
      await detectionAPI.reject(detection.id);
      loadDetections(); // Refresh to show updated status
    } catch (error) {
      console.error('Failed to reject detection:', error);
      alert('Failed to reject evidence. You may not have permission.');
    } finally {
      setActionInProgress(null);
    }
  };

  const getStatusInfo = (detection) => {
    if (detection.operator_action === 'verified' || detection.is_verified) {
      return {
        label: 'Verified',
        color: 'text-green-600',
        bgColor: 'bg-green-50 dark:bg-green-900/30',
        borderColor: 'border-green-200 dark:border-green-800',
        icon: <CheckCircle size={14} className="text-green-600" />,
        iconBg: 'bg-green-100 dark:bg-green-900/30',
        iconColor: 'text-green-600'
      };
    }
    if (detection.operator_action === 'rejected' || detection.is_false_positive) {
      return {
        label: 'Rejected',
        color: 'text-red-600',
        bgColor: 'bg-red-50 dark:bg-red-900/30',
        borderColor: 'border-red-200 dark:border-red-800',
        icon: <XCircle size={14} className="text-red-600" />,
        iconBg: 'bg-red-100 dark:bg-red-900/30',
        iconColor: 'text-red-600'
      };
    }
    return {
      label: 'Pending Review',
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50 dark:bg-yellow-900/30',
      borderColor: 'border-yellow-200 dark:border-yellow-800',
      icon: <Clock size={14} className="text-yellow-600" />,
      iconBg: 'bg-yellow-100 dark:bg-yellow-900/30',
      iconColor: 'text-yellow-600'
    };
  };

  const filteredDetections = detections.filter(d =>
    (d.event_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (d.detection_type || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pendingCount = detections.filter(d => !d.is_verified && d.operator_action !== 'verified' && d.operator_action !== 'rejected' && !d.is_false_positive).length;
  const verifiedCount = detections.filter(d => d.is_verified || d.operator_action === 'verified').length;
  const rejectedCount = detections.filter(d => d.is_false_positive || d.operator_action === 'rejected').length;

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Audit Trail</h1>
          <p className="text-sm text-gray-500 mt-1">Review and verify detection evidence before blockchain anchoring</p>
        </div>
        <div className="bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400 px-3 py-1 rounded-full text-xs font-bold flex items-center gap-2">
          <Shield size={14} />
          BLOCKCHAIN ACTIVE
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <Clock size={16} className="text-yellow-600" />
            <span className="text-xs font-bold uppercase text-yellow-700 dark:text-yellow-400">Pending</span>
          </div>
          <p className="text-2xl font-bold text-yellow-800 dark:text-yellow-300">{pendingCount}</p>
        </div>
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle size={16} className="text-green-600" />
            <span className="text-xs font-bold uppercase text-green-700 dark:text-green-400">Verified</span>
          </div>
          <p className="text-2xl font-bold text-green-800 dark:text-green-300">{verifiedCount}</p>
        </div>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <XCircle size={16} className="text-red-600" />
            <span className="text-xs font-bold uppercase text-red-700 dark:text-red-400">Rejected</span>
          </div>
          <p className="text-2xl font-bold text-red-800 dark:text-red-300">{rejectedCount}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4" />
            <input
              type="text"
              placeholder="Search by Event ID or Detection Type..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
        </div>

        {/* Evidence List */}
        <div className="divide-y divide-gray-100">
          {filteredDetections.length > 0 ? (
            filteredDetections.map((detection) => {
              const statusInfo = getStatusInfo(detection);
              const isPending = !detection.is_verified && detection.operator_action !== 'verified' && detection.operator_action !== 'rejected' && !detection.is_false_positive;
              const isProcessing = actionInProgress === detection.id;

              return (
                <div key={detection.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                  <div className="flex items-start gap-4">
                    {/* Status Icon */}
                    <div className="mt-1">
                      <div className={`h-8 w-8 rounded-full ${statusInfo.iconBg} flex items-center justify-center`}>
                        {statusInfo.icon}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1">
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                            {detection.detection_type?.replace('_', ' ') || 'Detection'}
                          </h3>
                          <p className="text-xs text-gray-500 mt-0.5">
                            Event: <span className="font-mono bg-gray-100 dark:bg-gray-700 px-1 rounded">{detection.event_id || `EVT-${detection.id}`}</span>
                            {' · '}Camera {detection.camera_id}
                            {detection.confidence && ` · ${(detection.confidence * 100).toFixed(1)}% confidence`}
                          </p>
                        </div>
                        <div className="flex items-center text-xs text-gray-500">
                          <Clock size={12} className="mr-1" />
                          {formatTimestamp(detection.timestamp)}
                        </div>
                      </div>

                      <div className="mt-2 flex items-center gap-3">
                        {/* Status Badge */}
                        <span className={`text-xs font-bold px-2 py-1 rounded-lg border ${statusInfo.bgColor} ${statusInfo.borderColor} ${statusInfo.color} flex items-center gap-1`}>
                          {statusInfo.icon}
                          {statusInfo.label}
                        </span>

                        {detection.blockchain_tx_id && (
                          <span className="text-xs font-mono text-gray-400 flex items-center bg-gray-50 dark:bg-gray-700 px-2 py-1 rounded border border-gray-100 dark:border-gray-600">
                            <LinkIcon size={10} className="mr-1" />
                            TX: {detection.blockchain_tx_id.substring(0, 20)}...
                          </span>
                        )}

                        {/* Verify/Reject Buttons */}
                        {isPending && (
                          <div className="flex items-center gap-2 ml-auto">
                            <button
                              onClick={() => handleVerify(detection)}
                              disabled={isProcessing}
                              className="px-3 py-1.5 text-xs font-bold bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-1.5 transition-colors disabled:opacity-50"
                            >
                              <CheckCircle size={14} />
                              {isProcessing ? 'Processing...' : 'Verify'}
                            </button>
                            <button
                              onClick={() => handleReject(detection)}
                              disabled={isProcessing}
                              className="px-3 py-1.5 text-xs font-bold bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center gap-1.5 transition-colors disabled:opacity-50"
                            >
                              <XCircle size={14} />
                              {isProcessing ? 'Processing...' : 'Reject'}
                            </button>
                          </div>
                        )}

                        {!isPending && (
                          <span className="ml-auto text-xs text-gray-400 italic">
                            Reviewed
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="p-12 text-center text-gray-500">
              <Shield className="h-12 w-12 mx-auto text-gray-300 mb-3" />
              <p>No audit entries found matching your criteria</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuditPage;