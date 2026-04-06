import React from 'react';
import { Video, VideoOff, Signal, SignalHigh, SignalLow } from 'lucide-react';

const CameraGrid = ({ cameras, onCameraSelect }) => {
  const getSignalIcon = (health) => {
    switch (health) {
      case 'healthy':
        return <SignalHigh className="w-4 h-4 text-green-500" />;
      case 'degraded':
        return <Signal className="w-4 h-4 text-yellow-500" />;
      default:
        return <SignalLow className="w-4 h-4 text-red-500" />;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {cameras.map((camera) => (
        <div
          key={camera.id}
          onClick={() => onCameraSelect(camera)}
          className="bg-white rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
        >
          {/* Video Feed Placeholder */}
          <div className="relative bg-gray-900 aspect-video">
            {camera.is_online ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <Video className="w-12 h-12 text-gray-600" />
                <span className="absolute top-2 right-2 px-2 py-1 bg-red-600 text-white text-xs rounded-full animate-pulse">
                  ● LIVE
                </span>
              </div>
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <VideoOff className="w-12 h-12 text-gray-600" />
                <span className="absolute top-2 right-2 px-2 py-1 bg-gray-600 text-white text-xs rounded-full">
                  OFFLINE
                </span>
              </div>
            )}
          </div>

          {/* Camera Info */}
          <div className="p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-gray-900">{camera.name}</h3>
                <p className="text-sm text-gray-500">{camera.location}</p>
              </div>
              {getSignalIcon(camera.health_status)}
            </div>

            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>{camera.resolution_width}x{camera.resolution_height}</span>
              <span>{camera.fps} FPS</span>
              <span className={`px-2 py-1 rounded-full ${
                camera.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
              }`}>
                {camera.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default CameraGrid;