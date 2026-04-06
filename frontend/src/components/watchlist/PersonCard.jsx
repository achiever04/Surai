import React, { useState } from 'react';
import { User, AlertTriangle, Eye, Edit, Trash2, X } from 'lucide-react';
import axios from 'axios';

const PersonCard = ({ person, onUpdate, onDelete }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [personDetails, setPersonDetails] = useState(null);
  const [loading, setLoading] = useState(false);

  const getRiskColor = (level) => {
    const colors = {
      low: 'bg-green-100 text-green-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800'
    };
    return colors[person.risk_level] || colors.low;
  };

  const handleViewDetails = async () => {
    setLoading(true);
    try {
      const token = sessionStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await axios.get(`${apiBase}/api/v1/watchlist/${person.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPersonDetails(response.data);
      setShowDetails(true);
    } catch (error) {
      console.error('Failed to fetch person details:', error);
      alert('Failed to load person details');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-4">
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                <User className="w-6 h-6 text-gray-400" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">{person.name}</h3>
                <p className="text-sm text-gray-500">{person.person_id}</p>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Category</span>
              <span className="text-sm font-medium capitalize">
                {person.category.replace('_', ' ')}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Risk Level</span>
              <span className={`px-2 py-1 text-xs rounded-full ${getRiskColor()}`}>
                {person.risk_level.toUpperCase()}
              </span>
            </div>

            {person.age && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Age</span>
                <span className="text-sm font-medium">{person.age}</span>
              </div>
            )}

            {person.last_seen_at && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Last Seen</span>
                <span className="text-sm font-medium">
                  {new Date(person.last_seen_at).toLocaleDateString()}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Detections</span>
              <span className="text-sm font-medium">{person.total_detections}</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-t border-gray-200">
          <button
            onClick={handleViewDetails}
            disabled={loading}
            className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            <Eye className="w-4 h-4" />
            <span>{loading ? 'Loading...' : 'View Details'}</span>
          </button>

          <button
            onClick={() => onUpdate(person)}
            className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-700"
          >
            <Edit className="w-4 h-4" />
            <span>Edit</span>
          </button>

          <button
            onClick={() => onDelete(person)}
            className="flex items-center space-x-1 text-sm text-red-600 hover:text-red-700"
          >
            <Trash2 className="w-4 h-4" />
            <span>Delete</span>
          </button>
        </div>
      </div>

      {/* Details Modal */}
      {showDetails && personDetails && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Person Details</h2>
              <button
                onClick={() => setShowDetails(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Basic Info */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Basic Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Name:</span>
                    <p className="font-medium">{personDetails.name}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Person ID:</span>
                    <p className="font-medium">{personDetails.person_id}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Category:</span>
                    <p className="font-medium capitalize">{personDetails.category.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Risk Level:</span>
                    <span className={`px-2 py-1 text-xs rounded-full ${getRiskColor()}`}>
                      {personDetails.risk_level.toUpperCase()}
                    </span>
                  </div>
                  {personDetails.age && (
                    <div>
                      <span className="text-sm text-gray-600">Age:</span>
                      <p className="font-medium">{personDetails.age}</p>
                    </div>
                  )}
                  {personDetails.gender && (
                    <div>
                      <span className="text-sm text-gray-600">Gender:</span>
                      <p className="font-medium capitalize">{personDetails.gender}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Photos */}
              {personDetails.photos && personDetails.photos.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Enrolled Photos ({personDetails.photos.length})
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {personDetails.photos.map((photo, index) => (
                      <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                        <img
                          src={photo}
                          alt={`${personDetails.name} - Photo ${index + 1}`}
                          className="w-full h-48 object-cover"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              {personDetails.description && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Description</h3>
                  <p className="text-gray-700">{personDetails.description}</p>
                </div>
              )}

              {/* Notes */}
              {personDetails.notes && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Notes</h3>
                  <p className="text-gray-700">{personDetails.notes}</p>
                </div>
              )}

              {/* Stats */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Statistics</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Total Detections:</span>
                    <p className="font-medium">{personDetails.total_detections}</p>
                  </div>
                  {personDetails.last_seen_at && (
                    <div>
                      <span className="text-sm text-gray-600">Last Seen:</span>
                      <p className="font-medium">
                        {new Date(personDetails.last_seen_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                  <div>
                    <span className="text-sm text-gray-600">Enrolled:</span>
                    <p className="font-medium">
                      {new Date(personDetails.enrolled_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Number of Photos:</span>
                    <p className="font-medium">{personDetails.num_photos}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default PersonCard;