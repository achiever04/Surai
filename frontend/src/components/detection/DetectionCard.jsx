import React from 'react';
import { Eye, AlertTriangle, Calendar, MapPin } from 'lucide-react';
import { format } from 'date-fns';

const DetectionCard = ({ detection, onClick }) => {
  return (
    <div
      onClick={() => onClick(detection)}
      className="bg-white rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow cursor-pointer border border-gray-200"
    >
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0">
          <div className="w-20 h-20 bg-gray-200 rounded-lg flex items-center justify-center">
            <Eye className="w-8 h-8 text-gray-400" />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-2">
            <span className={`px-2 py-1 text-xs rounded-full ${
              detection.detection_type === 'face_match' 
                ? 'bg-red-100 text-red-800' 
                : 'bg-blue-100 text-blue-800'
            }`}>
              {detection.detection_type.replace('_', ' ').toUpperCase()}
            </span>
            <span className="text-sm font-medium text-gray-900">
              {Math.round(detection.confidence * 100)}% confidence
            </span>
          </div>

          <div className="space-y-1">
            <div className="flex items-center text-sm text-gray-600">
              <Calendar className="w-3 h-3 mr-1" />
              {format(new Date(detection.timestamp), 'MMM dd, yyyy HH:mm:ss')}
            </div>
            <div className="flex items-center text-sm text-gray-600">
              <MapPin className="w-3 h-3 mr-1" />
              Camera {detection.camera_id}
            </div>
          </div>

          {detection.emotion && (
            <div className="mt-2 text-sm text-gray-600">
              Emotion: <span className="font-medium">{detection.emotion}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DetectionCard;