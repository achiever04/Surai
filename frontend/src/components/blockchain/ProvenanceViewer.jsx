import React from 'react';
import { Shield, User, Calendar, FileText } from 'lucide-react';

const ProvenanceViewer = ({ provenance }) => {
  if (!provenance) {
    return <div>No provenance data available</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-xl font-bold mb-4 flex items-center">
        <Shield className="w-6 h-6 mr-2 text-blue-600" />
        Evidence Provenance
      </h3>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-gray-500">Event ID</div>
            <div className="font-mono text-sm">{provenance.event_id}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Blockchain TX</div>
            <div className="font-mono text-sm">{provenance.blockchain_tx_id}</div>
          </div>
        </div>

        <div>
          <div className="text-sm text-gray-500 mb-2">Evidence Hash</div>
          <div className="font-mono text-sm bg-gray-100 p-2 rounded">
            {provenance.clip_hash}
          </div>
        </div>

        <div>
          <h4 className="font-medium mb-3 flex items-center">
            <FileText className="w-4 h-4 mr-2" />
            Chain of Custody
          </h4>
          
          <div className="space-y-3">
            {provenance.chain_of_custody?.map((event, index) => (
              <div key={index} className="flex items-start space-x-3 pl-4 border-l-2 border-blue-500">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="font-medium">{event.actor}</span>
                    <span className="text-sm text-gray-500">- {event.action}</span>
                  </div>
                  <div className="flex items-center space-x-2 mt-1 text-sm text-gray-500">
                    <Calendar className="w-3 h-3" />
                    <span>{new Date(event.timestamp).toLocaleString()}</span>
                  </div>
                  {event.notes && (
                    <div className="mt-1 text-sm text-gray-600">{event.notes}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={`mt-4 p-4 rounded-lg ${
          provenance.is_verified ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          <div className="flex items-center space-x-2">
            {provenance.is_verified ? (
              <>
                <Shield className="w-5 h-5 text-green-600" />
                <span className="font-medium text-green-900">Evidence Verified</span>
              </>
            ) : (
              <>
                <Shield className="w-5 h-5 text-red-600" />
                <span className="font-medium text-red-900">Verification Failed</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProvenanceViewer;