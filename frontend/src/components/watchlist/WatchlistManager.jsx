import React, { useState } from 'react';
import { Plus, Search, Filter } from 'lucide-react';
import PersonCard from './PersonCard';
import EnrollmentForm from './EnrollmentForm';

const WatchlistManager = ({ persons, onEnroll, onUpdate, onDelete }) => {
  const [showEnrollForm, setShowEnrollForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');

  const filteredPersons = persons.filter(person => {
    const matchesSearch = person.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = filterCategory === 'all' || person.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Categories</option>
            <option value="missing">Missing</option>
            <option value="criminal">Criminal</option>
            <option value="vip">VIP</option>
            <option value="person_of_interest">Person of Interest</option>
          </select>
        </div>

        <button
          onClick={() => setShowEnrollForm(true)}
          className="flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          <span>Enroll Person</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredPersons.map((person) => (
          <PersonCard
            key={person.id}
            person={person}
            onUpdate={onUpdate}
            onDelete={onDelete}
          />
        ))}
      </div>

      {showEnrollForm && (
        <EnrollmentForm
          onClose={() => setShowEnrollForm(false)}
          onSubmit={onEnroll}
        />
      )}
    </div>
  );
};

export default WatchlistManager;