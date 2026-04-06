import React, { useState, useEffect } from 'react';
import { detectionAPI } from '../services/api';
import { FileText, Download, Eye, Shield, Calendar, Trash2, X, User, CheckSquare, Square, XCircle, Clock, Camera } from 'lucide-react';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useWebSocket } from '../hooks/useWebSocket';
import { formatTimestamp } from '../utils/formatTime';

const EvidencePage = () => {
  const [detections, setDetections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDetection, setSelectedDetection] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  // Listen for real-time new evidence/detections
  useWebSocket('new_detection', (data) => {
    console.log('Evidence: New detection received:', data);
    loadEvidence(); // Refresh evidence list
  });

  // Listen for deletion events
  useWebSocket('detection_deleted', (data) => {
    console.log('Evidence: Detection deleted:', data);
    loadEvidence(); // Refresh evidence list
  });

  useEffect(() => {
    loadEvidence();
  }, []);

  const loadEvidence = async () => {
    try {
      const response = await detectionAPI.getAll({ limit: 50 });
      setDetections(response.data);
      setSelectedIds(new Set()); // Clear selection on refresh
    } catch (error) {
      console.error('Failed to load evidence:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Multi-select handlers
  const toggleSelectAll = () => {
    if (selectedIds.size === detections.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(detections.map(d => d.id)));
    }
  };

  const toggleSelect = (id) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Delete ${selectedIds.size} evidence record(s)? This action cannot be undone.`)) return;

    setIsDeleting(true);
    try {
      await detectionAPI.bulkDelete(Array.from(selectedIds));
      setSelectedIds(new Set());
      loadEvidence();
    } catch (err) {
      alert("Failed to delete selected evidence. You may not have permission.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleExportReport = () => {
    if (detections.length === 0) {
      alert('No evidence data to export');
      return;
    }

    // Generate CSV content
    const headers = ['Event ID', 'Type', 'Camera', 'Timestamp', 'Verification Status', 'Confidence'];
    const csvRows = [headers.join(',')];

    detections.forEach(detection => {
      const verStatus = detection.operator_action === 'verified' ? 'Verified'
        : detection.operator_action === 'rejected' ? 'Rejected' : 'Not Verified';
      const row = [
        detection.event_id || `EVT-${detection.id}`,
        detection.detection_type || 'Unknown',
        `Camera ${detection.camera_id}`,
        new Date(detection.timestamp).toISOString(),
        verStatus,
        detection.confidence ? `${(detection.confidence * 100).toFixed(1)}%` : 'N/A'
      ];
      csvRows.push(row.join(','));
    });

    const csvContent = csvRows.join('\n');

    // Create and trigger download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `evidence_report_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this evidence? This action cannot be undone.")) return;
    try {
      await detectionAPI.delete(id);
      loadEvidence(); // Refresh list immediately
    } catch (err) {
      alert("Failed to delete evidence. You may not have permission.");
    }
  };

  const handleViewDetails = async (detection) => {
    try {
      const response = await detectionAPI.getById(detection.id);
      setSelectedDetection(response.data);
    } catch (error) {
      console.error('Failed to fetch detection details:', error);
      setSelectedDetection(detection);
    }
  };

  // Render verification badge based on operator_action/is_verified
  const renderVerificationBadge = (detection) => {
    if (detection.operator_action === 'verified' || detection.is_verified) {
      return (
        <div className="flex items-center gap-1.5 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2 py-1 rounded-lg w-fit border border-green-100 dark:border-green-800">
          <Shield size={14} />
          <span className="text-xs font-bold">Verified on Chain</span>
        </div>
      );
    }
    if (detection.operator_action === 'rejected' || detection.is_false_positive) {
      return (
        <div className="flex items-center gap-1.5 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-2 py-1 rounded-lg w-fit border border-red-100 dark:border-red-800">
          <XCircle size={14} />
          <span className="text-xs font-bold">Rejected</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5 bg-yellow-50 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 px-2 py-1 rounded-lg w-fit border border-yellow-100 dark:border-yellow-800">
        <Clock size={14} />
        <span className="text-xs font-bold">Not Verified</span>
      </div>
    );
  };

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Evidence Management</h1>
          <p className="text-sm text-gray-500">Secure storage and retrieval of surveillance evidence</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
          <h2 className="font-semibold text-gray-800 flex items-center gap-2">
            <FileText size={18} />
            Evidence Logs
            {selectedIds.size > 0 && (
              <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 rounded-full font-medium">
                {selectedIds.size} selected
              </span>
            )}
          </h2>
          <div className="flex items-center gap-2">
            {selectedIds.size > 0 && (
              <button
                onClick={handleBulkDelete}
                disabled={isDeleting}
                className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50"
              >
                <Trash2 size={14} />
                {isDeleting ? 'Deleting...' : `Delete Selected (${selectedIds.size})`}
              </button>
            )}
            <button
              onClick={handleExportReport}
              className="px-3 py-1.5 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center gap-2 transition-colors text-gray-700"
            >
              <Download size={16} />
              Export Report
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-4 w-10">
                  <button onClick={toggleSelectAll} className="text-gray-400 hover:text-gray-600 transition-colors" title="Select All">
                    {selectedIds.size === detections.length && detections.length > 0 ? (
                      <CheckSquare size={18} className="text-blue-600" />
                    ) : (
                      <Square size={18} />
                    )}
                  </button>
                </th>
                <th className="px-6 py-4">Event ID</th>
                <th className="px-6 py-4">Type</th>
                <th className="px-6 py-4">Source</th>
                <th className="px-6 py-4">Timestamp</th>
                <th className="px-6 py-4">Verification</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {detections.length > 0 ? (
                detections.map((detection) => (
                  <tr
                    key={detection.id}
                    className={`hover:bg-blue-50/50 dark:hover:bg-blue-900/20 transition-colors ${selectedIds.has(detection.id) ? 'bg-blue-50 dark:bg-blue-900/10' : ''
                      }`}
                  >
                    <td className="px-4 py-4">
                      <button
                        onClick={() => toggleSelect(detection.id)}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        {selectedIds.has(detection.id) ? (
                          <CheckSquare size={18} className="text-blue-600" />
                        ) : (
                          <Square size={18} />
                        )}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-mono text-xs text-blue-600 font-medium">
                      {detection.event_id || `EVT-${detection.id}`}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 capitalize border border-blue-200 dark:border-blue-800">
                        {detection.detection_type?.replace('_', ' ') || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      Camera {detection.camera_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 flex items-center gap-2">
                      <Calendar size={14} className="text-gray-400" />
                      {formatTimestamp(detection.timestamp)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {renderVerificationBadge(detection)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => handleViewDetails(detection)}
                          className="p-2 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                          title="View Details"
                        >
                          <Eye size={18} />
                        </button>
                        <button
                          onClick={() => handleDelete(detection.id)}
                          className="p-2 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                          title="Delete Evidence"
                        >
                          <Trash2 size={18} />
                        </button>
                        <button className="p-2 text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg transition-colors" title="Download Evidence">
                          <Download size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="7" className="px-6 py-12 text-center text-gray-500">
                    No evidence records found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* View Details Modal */}
      {selectedDetection && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto mx-4">
            <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <FileText className="w-6 h-6 text-blue-600" />
                Evidence Details
              </h2>
              <button
                onClick={() => setSelectedDetection(null)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Event ID</p>
                  <p className="text-sm font-mono font-medium">{selectedDetection.event_id || `EVT-${selectedDetection.id}`}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Detection Type</p>
                  <p className="text-sm font-medium capitalize">{selectedDetection.detection_type?.replace('_', ' ')}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Camera</p>
                  <p className="text-sm font-medium">Camera {selectedDetection.camera_id}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Confidence</p>
                  <p className="text-sm font-medium">{selectedDetection.confidence ? `${(selectedDetection.confidence * 100).toFixed(1)}%` : 'N/A'}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg col-span-2">
                  <p className="text-xs text-gray-500 uppercase mb-1">Timestamp</p>
                  <p className="text-sm font-medium">                      {formatTimestamp(selectedDetection.timestamp)}</p>
                </div>
                {/* Verification status */}
                <div className="col-span-2">
                  {renderVerificationBadge(selectedDetection)}
                </div>
                {selectedDetection.blockchain_tx_id && (
                  <div className="bg-green-50 p-3 rounded-lg col-span-2 border border-green-200">
                    <p className="text-xs text-green-700 uppercase mb-1 flex items-center gap-1">
                      <Shield size={12} />
                      Blockchain Transaction
                    </p>
                    <p className="text-xs font-mono text-green-800 break-all">{selectedDetection.blockchain_tx_id}</p>
                  </div>
                )}
              </div>

              {/* Detected Frame — captured at exact detection time */}
              {selectedDetection.detected_frame && (
                <div className="border-t border-gray-100 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <Camera className="w-4 h-4 text-blue-600" />
                    Detected Frame
                  </h4>
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <img
                      src={selectedDetection.detected_frame}
                      alt="Detection capture"
                      className="w-full object-contain max-h-64 bg-gray-900"
                    />
                    <div className="bg-gray-50 px-3 py-1.5 text-xs text-gray-500 flex items-center gap-1.5">
                      <Clock size={12} />
                      Captured: {formatTimestamp(selectedDetection.timestamp)}
                    </div>
                  </div>
                </div>
              )}

              {/* Matched Person Photos */}
              {selectedDetection.matched_person_name && (
                <div className="border-t border-gray-100 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <User className="w-4 h-4 text-blue-600" />
                    Matched Person
                  </h4>
                  <div className="bg-blue-50 p-3 rounded-lg border border-blue-100 mb-3">
                    <p className="text-sm font-medium text-blue-900">{selectedDetection.matched_person_name}</p>
                    <p className="text-xs text-blue-700 capitalize mt-0.5">{selectedDetection.matched_person_category?.replace('_', ' ')}</p>
                  </div>
                  {selectedDetection.matched_person_photos && selectedDetection.matched_person_photos.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 uppercase mb-2">Enrolled Photos ({selectedDetection.matched_person_photos.length})</p>
                      <div className="grid grid-cols-3 gap-2">
                        {selectedDetection.matched_person_photos.map((photo, index) => (
                          <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                            <img
                              src={photo}
                              alt={`${selectedDetection.matched_person_name} - Photo ${index + 1}`}
                              className="w-full h-28 object-cover"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Age Progression & Detection Details */}
              {selectedDetection.detection_metadata && (
                <div className="border-t border-gray-100 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">Detection Details</h4>
                  <div className="grid grid-cols-2 gap-3">
                    {selectedDetection.detection_metadata.detected_age && (
                      <div className="bg-purple-50 p-3 rounded-lg border border-purple-100">
                        <p className="text-xs text-purple-600 uppercase mb-1">Detected Age</p>
                        <p className="text-lg font-bold text-purple-800">{Math.round(selectedDetection.detection_metadata.detected_age)} yrs</p>
                      </div>
                    )}
                    {selectedDetection.detection_metadata.registered_age != null && (
                      <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                        <p className="text-xs text-blue-600 uppercase mb-1">Registered Age</p>
                        <p className="text-lg font-bold text-blue-800">{selectedDetection.detection_metadata.registered_age} yrs</p>
                      </div>
                    )}
                    {selectedDetection.detection_metadata.age_gap != null && (
                      <div className={`col-span-2 rounded-lg p-3 border ${
                        selectedDetection.detection_metadata.age_gap === 0
                          ? 'bg-green-50 border-green-200'
                          : 'bg-amber-50 border-amber-200'
                      }`}>
                        <p className={`text-xs uppercase mb-1 ${
                          selectedDetection.detection_metadata.age_gap === 0 ? 'text-green-700' : 'text-amber-700'
                        }`}>Age Progression Gap</p>
                        {selectedDetection.detection_metadata.age_gap === 0 ? (
                          <p className="text-sm font-bold text-green-800">No Age Gap — ages match</p>
                        ) : (
                          <>
                            <p className="text-lg font-bold text-amber-800">{selectedDetection.detection_metadata.age_gap} years</p>
                            <p className="text-xs text-amber-600 mt-1">{selectedDetection.detection_metadata.age_gap_label}</p>
                          </>
                        )}
                      </div>
                    )}
                    {selectedDetection.detection_metadata.emotion && (
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase mb-1">Emotion</p>
                        <p className="text-sm font-medium capitalize">{selectedDetection.detection_metadata.emotion}</p>
                      </div>
                    )}
                    {selectedDetection.detection_metadata.pose_type && (
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <p className="text-xs text-gray-500 uppercase mb-1">Pose Type</p>
                        <p className="text-sm font-medium capitalize">{selectedDetection.detection_metadata.pose_type}</p>
                      </div>
                    )}
                    {selectedDetection.detection_metadata.has_weapon && (
                      <div className="bg-red-50 p-3 rounded-lg border border-red-200 col-span-2">
                        <p className="text-xs text-red-600 uppercase mb-1">Weapon Detected</p>
                        <p className="text-sm font-bold text-red-800">
                          {selectedDetection.detection_metadata.weapons_detected?.map(w => w.class || w).join(', ') || 'Yes'}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {selectedDetection.detection_metadata && (
                <div className="border-t border-gray-100 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Raw Metadata</h4>
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <pre className="text-xs text-gray-600 overflow-auto">
                      {JSON.stringify(selectedDetection.detection_metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-gray-100 p-4">
              <button
                onClick={() => setSelectedDetection(null)}
                className="w-full py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 rounded-lg font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EvidencePage;