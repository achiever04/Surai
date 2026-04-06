import React from 'react';
import { X, Download, Shield, AlertTriangle } from 'lucide-react';

const DetectionModal = ({ detection, onClose }) => {
  if (!detection) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold">Detection Details</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-6">
            <div className="col-span-2 md:col-span-1">
              <div className="aspect-video bg-gray-200 rounded-lg flex items-center justify-center">
                <span className="text-gray-400">Evidence Image</span>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="text-sm text-gray-500">Event ID</div>
                <div className="font-mono text-sm">{detection.event_id}</div>
              </div>

              <div>
                <div className="text-sm text-gray-500">Detection Type</div>
                <div className="font-medium">{detection.detection_type}</div>
              </div>

              <div>
                <div className="text-sm text-gray-500">Confidence</div>
                <div className="font-medium">{Math.round(detection.confidence * 100)}%</div>
              </div>

              {detection.emotion && (
                <div>
                  <div className="text-sm text-gray-500">Emotion</div>
                  <div className="font-medium capitalize">{detection.emotion}</div>
                </div>
              )}
            </div>
          </div>

          {detection.blockchain_tx_id && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center space-x-2 text-green-900">
                <Shield className="w-5 h-5" />
                <span className="font-medium">Blockchain Verified</span>
              </div>
              <div className="mt-2 text-sm text-green-700 font-mono">
                TX: {detection.blockchain_tx_id}
              </div>
            </div>
          )}

          <div className="flex items-center space-x-3">
            <button className="flex-1 flex items-center justify-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
              <Download className="w-4 h-4" />
              <span>Download Evidence</span>
            </button>
            <button className="flex items-center space-x-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200">
              <Shield className="w-4 h-4" />
              <span>View Provenance</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DetectionModal;