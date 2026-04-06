import React, { useState } from 'react';
import { VideoOff, RefreshCw, Eye, EyeOff } from 'lucide-react';

const CameraFeed = ({ camera }) => {
  const [error, setError] = useState(false);
  const [key, setKey] = useState(0);

  // Detection overlay controls
  const [showDetections, setShowDetections] = useState(true);
  const [showWatchlistIds, setShowWatchlistIds] = useState(true);
  const [showConfidence, setShowConfidence] = useState(true);
  const [showEmotion, setShowEmotion] = useState(true);
  const [showAge, setShowAge] = useState(true);
  const [showPose, setShowPose] = useState(true);
  const [showControls, setShowControls] = useState(false);

  const token = sessionStorage.getItem('access_token');

  // Use annotated stream endpoint with detection overlays
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const streamUrl = `${apiBase}/api/v1/cameras/${camera.id}/stream/annotated?` +
    `token=${token}&` +
    `show_detections=${showDetections}&` +
    `show_watchlist_ids=${showWatchlistIds}&` +
    `show_confidence=${showConfidence}&` +
    `show_emotion=${showEmotion}&` +
    `show_age=${showAge}&` +
    `show_pose=${showPose}&` +
    `_=${key}`;

  const handleRetry = () => {
    setError(false);
    setKey(prev => prev + 1);
  };

  return (
    <div className="relative w-full h-full bg-black flex items-center justify-center overflow-hidden">
      {!error ? (
        <>
          <img
            key={key}
            src={streamUrl}
            alt="Camera Feed"
            className="w-full h-full object-contain"
            onError={() => {
              console.error(`Stream failed for camera ${camera.id}`);
              setError(true);
            }}
            onLoad={() => console.log(`Annotated stream loaded for camera ${camera.id}`)}
          />

          {/* LIVE Indicator */}
          <div className="absolute top-3 right-3 flex items-center gap-2 bg-black/60 px-3 py-1 rounded-full">
            <span className="flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
            <span className="text-xs font-bold text-white tracking-wider">LIVE</span>
          </div>

          {/* Detection Controls Toggle */}
          <div className="absolute top-3 left-3">
            <button
              onClick={() => setShowControls(!showControls)}
              className="bg-black/60 hover:bg-black/80 p-2 rounded-full transition-colors"
              title={showControls ? "Hide controls" : "Show controls"}
            >
              {showControls ? <EyeOff size={16} className="text-white" /> : <Eye size={16} className="text-white" />}
            </button>
          </div>

          {/* Detection Controls Panel */}
          {showControls && (
            <div className="absolute top-14 left-3 bg-black/80 p-3 rounded-lg space-y-2 text-xs text-white">
              <div className="font-bold mb-2 text-sm border-b border-gray-600 pb-2">Detection Overlays</div>

              <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded">
                <input
                  type="checkbox"
                  checked={showDetections}
                  onChange={(e) => setShowDetections(e.target.checked)}
                  className="cursor-pointer"
                />
                <span>Show All Detections</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded">
                <input
                  type="checkbox"
                  checked={showWatchlistIds}
                  onChange={(e) => setShowWatchlistIds(e.target.checked)}
                  disabled={!showDetections}
                  className="cursor-pointer"
                />
                <span className={!showDetections ? 'opacity-50' : ''}>Watchlist IDs</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded">
                <input
                  type="checkbox"
                  checked={showConfidence}
                  onChange={(e) => setShowConfidence(e.target.checked)}
                  disabled={!showDetections}
                  className="cursor-pointer"
                />
                <span className={!showDetections ? 'opacity-50' : ''}>Confidence Scores</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded">
                <input
                  type="checkbox"
                  checked={showEmotion}
                  onChange={(e) => setShowEmotion(e.target.checked)}
                  disabled={!showDetections}
                  className="cursor-pointer"
                />
                <span className={!showDetections ? 'opacity-50' : ''}>Emotion Labels</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded">
                <input
                  type="checkbox"
                  checked={showAge}
                  onChange={(e) => setShowAge(e.target.checked)}
                  disabled={!showDetections}
                  className="cursor-pointer"
                />
                <span className={!showDetections ? 'opacity-50' : ''}>Age Estimates</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer hover:bg-white/10 p-1 rounded">
                <input
                  type="checkbox"
                  checked={showPose}
                  onChange={(e) => setShowPose(e.target.checked)}
                  disabled={!showDetections}
                  className="cursor-pointer"
                />
                <span className={!showDetections ? 'opacity-50' : ''}>Pose Skeleton</span>
              </label>

              {/* Legend */}
              <div className="mt-3 pt-2 border-t border-gray-600 space-y-1">
                <div className="font-bold mb-1">Color Legend:</div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 border-2 border-green-500"></div>
                  <span>Face</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 border-2 border-yellow-400"></div>
                  <span>Watchlist Match</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 border-2 border-red-500"></div>
                  <span>Weapon</span>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center text-gray-400 p-4">
          <VideoOff className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p className="text-sm mb-3">Stream unavailable</p>
          <p className="text-xs mb-3 text-red-400">Check backend logs</p>
          <button
            onClick={handleRetry}
            className="px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded-full text-xs flex items-center gap-2 mx-auto"
          >
            <RefreshCw size={12} /> Retry
          </button>
        </div>
      )}
    </div>
  );
};

export default CameraFeed;