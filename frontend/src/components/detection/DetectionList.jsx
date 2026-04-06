import React from 'react';
import { Eye, AlertTriangle, CheckCircle, Clock, MapPin } from 'lucide-react';
import { format } from 'date-fns';

const DetectionList = ({ detections, onDetectionClick }) => {
  const getTypeColor = (type) => {
    const colors = {
      face_match: 'bg-red-100 text-red-800',
      suspicious_behavior: 'bg-orange-100 text-orange-800',
      emotion_alert: 'bg-yellow-100 text-yellow-800',
      loitering: 'bg-blue-100 text-blue-800',
      intrusion: 'bg-purple-100 text-purple-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  const getTypeIcon = (type) => {
    if (type === 'face_match') return <AlertTriangle className="w-4 h-4" />;
    return <Eye className="w-4 h-4" />;
  };

  return (
    <div className="space-y-3">
      {detections.map((detection) => (
        <div
          key={detection.id}
          onClick={() => onDetectionClick(detection)}
          className="bg-white rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow cursor-pointer border border-gray-200"
        >
          <div className="flex items-start justify-between">
            {/* Left: Detection Info */}
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-2">
                <span className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(detection.detection_type)}`}>
                  {getTypeIcon(detection.detection_type)}
                  <span>{detection.detection_type.replace('_', ' ').toUpperCase()}</span>
                </span>
                
                {detection.is_verified && (
                  <span className="flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <CheckCircle className="w-3 h-3" />
                    <span>Verified</span>
                  </span>
                )}
              </div>

              <div className="space-y-1 text-sm">
                <div className="flex items-center space-x-2 text-gray-600">
                  <Clock className="w-4 h-4" />
                  <span>{format(new Date(detection.timestamp), 'MMM dd, yyyy HH:mm:ss')}</span>
                </div>

                <div className="flex items-center space-x-2 text-gray-600">
                  <MapPin className="w-4 h-4" />
                  <span>Camera {detection.camera_id}</span>
                </div>

                {detection.emotion && (
                  <div className="text-gray-600">
                    <span className="font-medium">Emotion:</span> {detection.emotion}
                  </div>
                )}

                {detection.matched_person_id && (
                  <div className="text-red-600 font-medium">
                    ⚠️ Watchlist Match (ID: {detection.matched_person_id})
                  </div>
                )}
              </div>
            </div>

            {/* Right: Confidence Score */}
            <div className="ml-4 text-right">
              <div className="text-2xl font-bold text-gray-900">
                {Math.round(detection.confidence * 100)}%
              </div>
              <div className="text-xs text-gray-500">Confidence</div>
            </div>
          </div>

          {/* Event ID */}
          <div className="mt-3 pt-3 border-t border-gray-200">
            <span className="text-xs text-gray-500 font-mono">
              {detection.event_id}
            </span>
          </div>
        </div>
      ))}

      {detections.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <Eye className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>No detections found</p>
        </div>
      )}
    </div>
  );
};

export default DetectionList;