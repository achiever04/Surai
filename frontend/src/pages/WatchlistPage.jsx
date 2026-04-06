import React, { useState, useEffect } from 'react';
import { watchlistAPI } from '../services/api';
import { UserPlus, Search, AlertCircle, Trash2, Eye, X, User, Clock, MapPin, Camera } from 'lucide-react';
import LoadingSpinner from '../components/common/LoadingSpinner';
import Alert from '../components/common/Alert';
import EnrollmentForm from '../components/watchlist/EnrollmentForm';
import { useWebSocket } from '../hooks/useWebSocket';
import { formatTimestamp, formatDate } from '../utils/formatTime';

const WatchlistPage = () => {
  const [persons, setPersons] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [showEnrollModal, setShowEnrollModal] = useState(false);
  const [selectedPerson, setSelectedPerson] = useState(null); // For view modal
  const [recentMatch, setRecentMatch] = useState(null);

  // Listen for real-time watchlist matches
  useWebSocket('watchlist_match', (data) => {
    console.log('Watchlist: Match detected:', data);
    setRecentMatch(data);
    loadWatchlist();
    setTimeout(() => setRecentMatch(null), 10000);
  });

  useEffect(() => {
    loadWatchlist();
  }, []);

  const loadWatchlist = async () => {
    try {
      const response = await watchlistAPI.getAll();
      setPersons(response.data);
    } catch (error) {
      setError('Failed to load watchlist');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEnrollPerson = async (formData) => {
    try {
      const response = await watchlistAPI.create(formData);
      loadWatchlist();
      setShowEnrollModal(false);
      
      // AGE PROGRESSION: Show warning if detected age mismatches entered age
      const data = response.data || response;
      if (data.age_warning) {
        setTimeout(() => {
          alert(`⚠️ Age Verification Warning:\n\n${data.age_warning}\n\nPhoto-detected age: ~${data.photo_detected_age} years`);
        }, 300);
      }
    } catch (err) {
      setError('Failed to enroll person. Please try again.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this person from watchlist?")) return;
    try {
      await watchlistAPI.delete(id);
      loadWatchlist();
    } catch (err) {
      setError("Failed to delete person");
    }
  };

  const handleViewPerson = async (person) => {
    try {
      const response = await watchlistAPI.getById(person.id);
      setSelectedPerson(response.data);
    } catch (error) {
      console.error('Failed to fetch person details:', error);
      setSelectedPerson(person);
    }
  };

  const filteredPersons = persons.filter(person =>
    person.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    person.person_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getRiskColor = (level) => {
    const map = {
      low: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400',
      medium: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400',
      high: 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-400',
      critical: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
    };
    return map[level] || map.low;
  };

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">Watchlist Management</h1>
        <button
          onClick={() => setShowEnrollModal(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700 transition-colors shadow-sm"
        >
          <UserPlus size={20} />
          Add Person
        </button>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Search Bar */}
        <div className="p-4 border-b border-gray-100">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 h-5 w-5" />
            <input
              type="text"
              placeholder="Search by name or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3">Person</th>
                <th className="px-6 py-3">Category</th>
                <th className="px-6 py-3">Risk Level</th>
                <th className="px-6 py-3">Last Seen</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredPersons.map((person) => (
                <tr key={person.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="h-10 w-10 flex-shrink-0 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 font-bold">
                        {person.name.charAt(0)}
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">{person.name}</div>
                        <div className="text-xs text-gray-500">ID: {person.person_id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800 capitalize">
                      {person.category.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getRiskColor(person.risk_level)} uppercase`}>
                      {person.risk_level}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {person.last_seen_at ? formatDate(person.last_seen_at) : 'Never'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => handleViewPerson(person)}
                      className="text-gray-400 hover:text-blue-600 mr-3"
                      title="View Details"
                    >
                      <Eye size={18} />
                    </button>
                    <button
                      onClick={() => handleDelete(person.id)}
                      className="text-gray-400 hover:text-red-600"
                      title="Delete"
                    >
                      <Trash2 size={18} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredPersons.length === 0 && (
            <div className="text-center py-12">
              <AlertCircle className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No persons found matching your search</p>
            </div>
          )}
        </div>
      </div>

      {/* Enrollment Modal */}
      {showEnrollModal && (
        <EnrollmentForm
          onClose={() => setShowEnrollModal(false)}
          onSubmit={handleEnrollPerson}
        />
      )}

      {/* Person Details Modal */}
      {selectedPerson && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto mx-4">
            <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <User className="w-6 h-6 text-blue-600" />
                Person Details
              </h2>
              <button
                onClick={() => setSelectedPerson(null)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Header with avatar */}
              <div className="flex items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 font-bold text-2xl">
                  {selectedPerson.name.charAt(0)}
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-gray-900">{selectedPerson.name}</h3>
                  <p className="text-sm text-gray-500">ID: {selectedPerson.person_id}</p>
                </div>
              </div>

              {/* Info Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Category</p>
                  <p className="text-sm font-medium capitalize">{selectedPerson.category?.replace('_', ' ')}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Risk Level</p>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getRiskColor(selectedPerson.risk_level)} uppercase`}>
                    {selectedPerson.risk_level}
                  </span>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Age</p>
                  <p className="text-sm font-medium">{selectedPerson.age || 'Not specified'}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Gender</p>
                  <p className="text-sm font-medium capitalize">{selectedPerson.gender || 'Not specified'}</p>
                </div>
              </div>

              {/* Description */}
              {selectedPerson.description && (
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 uppercase mb-1">Description</p>
                  <p className="text-sm text-gray-700">{selectedPerson.description}</p>
                </div>
              )}

              {/* Detection Stats */}
              <div className="border-t border-gray-100 pt-4">
                <h4 className="text-sm font-semibold text-gray-700 mb-3">Detection Information</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span>Last Seen: {selectedPerson.last_seen_at ? formatTimestamp(selectedPerson.last_seen_at) : 'Never'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <MapPin className="w-4 h-4 text-gray-400" />
                    <span>Location: {selectedPerson.last_seen_location || 'Unknown'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Camera className="w-4 h-4 text-gray-400" />
                    <span>Total Detections: {selectedPerson.total_detections || 0}</span>
                  </div>
                </div>
              </div>

              {/* PHOTO DISPLAY FIX: Photos Section */}
              {selectedPerson.photos && selectedPerson.photos.length > 0 && (
                <div className="border-t border-gray-100 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">
                    Enrolled Photos ({selectedPerson.photos.length})
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {selectedPerson.photos.map((photo, index) => (
                      <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                        <img
                          src={photo}
                          alt={`${selectedPerson.name} - Photo ${index + 1}`}
                          className="w-full h-32 object-cover"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata */}
              <div className="border-t border-gray-100 pt-4 text-xs text-gray-500">
                <p>Enrolled by: {selectedPerson.enrolled_by || 'Unknown'}</p>
                <p>Enrolled at: {selectedPerson.enrolled_at ? formatTimestamp(selectedPerson.enrolled_at) : 'Unknown'}</p>
              </div>
            </div>

            <div className="border-t border-gray-100 p-4">
              <button
                onClick={() => setSelectedPerson(null)}
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

export default WatchlistPage;