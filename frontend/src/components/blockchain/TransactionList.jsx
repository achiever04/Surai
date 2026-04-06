import React from 'react';
import { ExternalLink, CheckCircle, XCircle, Clock } from 'lucide-react';

const TransactionList = ({ transactions }) => {
  const getStatusIcon = (status) => {
    switch (status) {
      case 'confirmed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Clock className="w-4 h-4 text-yellow-600" />;
    }
  };

  return (
    <div className="space-y-3">
      {transactions.map((tx) => (
        <div key={tx.tx_id} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-2">
                {getStatusIcon(tx.status)}
                <span className="font-medium text-gray-900">{tx.tx_type}</span>
              </div>
              
              <div className="space-y-1 text-sm text-gray-600">
                <div>
                  <span className="font-medium">TX ID:</span>
                  <span className="ml-2 font-mono">{tx.tx_id}</span>
                </div>
                <div>
                  <span className="font-medium">Entity:</span>
                  <span className="ml-2">{tx.entity_type}: {tx.entity_id}</span>
                </div>
                <div>
                  <span className="font-medium">Channel:</span>
                  <span className="ml-2">{tx.channel_name}</span>
                </div>
              </div>
            </div>

            <button className="ml-4 p-2 text-blue-600 hover:bg-blue-50 rounded">
              <ExternalLink className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500">
            {new Date(tx.created_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TransactionList;