import React from 'react';
import { Play, Pause, Settings, Trash2 } from 'lucide-react';

const CameraControls = ({ camera, onStart, onStop, onSettings, onDelete }) => {
  return (
    <div className="flex items-center space-x-2">
      {camera.is_active ? (
        <button
          onClick={onStop}
          className="flex items-center space-x-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100"
        >
          <Pause className="w-4 h-4" />
          <span>Stop</span>
        </button>
      ) : (
        <button
          onClick={onStart}
          className="flex items-center space-x-2 px-4 py-2 bg-green-50 text-green-600 rounded-lg hover:bg-green-100"
        >
          <Play className="w-4 h-4" />
          <span>Start</span>
        </button>
      )}

      <button
        onClick={onSettings}
        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
        title="Settings"
      >
        <Settings className="w-4 h-4" />
      </button>

      <button
        onClick={onDelete}
        className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
        title="Delete"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
};

export default CameraControls;