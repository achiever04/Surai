import React, { useState } from 'react';
import { X, Video, Globe, MapPin, Tag, Camera } from 'lucide-react';

const CameraForm = ({ onClose, onSubmit }) => {
  const [sourceType, setSourceType] = useState('rtsp'); // 'rtsp' or 'webcam'
  const [formData, setFormData] = useState({
    name: '',
    source_url: '',
    location: '',
    description: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const submissionData = {
        ...formData,
        source_type: sourceType,
        // If webcam, default URL to "0" (first device), else use input
        source_url: sourceType === 'webcam' ? '0' : formData.source_url
      };
      await onSubmit(submissionData);
      onClose();
    } catch (error) {
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <Video className="w-5 h-5 text-blue-600" />
            Add New Camera
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Source Type Selection */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <button
              type="button"
              onClick={() => setSourceType('rtsp')}
              className={`flex flex-col items-center justify-center p-3 rounded-lg border-2 transition-all ${sourceType === 'rtsp'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 text-gray-600'
                }`}
            >
              <Globe className="w-6 h-6 mb-1" />
              <span className="text-sm font-medium">IP / RTSP Camera</span>
            </button>
            <button
              type="button"
              onClick={() => setSourceType('webcam')}
              className={`flex flex-col items-center justify-center p-3 rounded-lg border-2 transition-all ${sourceType === 'webcam'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 text-gray-600'
                }`}
            >
              <Camera className="w-6 h-6 mb-1" />
              <span className="text-sm font-medium">Local Webcam</span>
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Camera Name</label>
            <input
              type="text"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Main Entrance"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          {sourceType === 'rtsp' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">RTSP Stream URL</label>
              <input
                type="text"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="rtsp://user:pass@192.168.1.10:554/stream"
                value={formData.source_url}
                onChange={(e) => setFormData({ ...formData, source_url: e.target.value })}
              />
            </div>
          )}

          {sourceType === 'webcam' && (
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300 text-sm rounded-lg flex items-start gap-2">
              <Camera className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <p>This will use the default webcam connected to the server/computer running the backend.</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
            <div className="relative">
              <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
              <input
                type="text"
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. Building A"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              />
            </div>
          </div>

          <div className="pt-2 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Adding...' : 'Add Camera'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CameraForm;