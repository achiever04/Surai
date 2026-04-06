import React from 'react';
import { X, AlertCircle, CheckCircle, AlertTriangle, Info } from 'lucide-react';

const Alert = ({ title, message, type = 'info', onClose }) => {
  // Map types to colors/icons
  const styles = {
    info: 'bg-blue-50 text-blue-800 border-blue-200',
    success: 'bg-green-50 text-green-800 border-green-200',
    warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
    error: 'bg-red-50 text-red-800 border-red-200',
  };

  const Icons = {
    info: Info,
    success: CheckCircle,
    warning: AlertTriangle,
    error: AlertCircle,
  };

  const Icon = Icons[type] || Info;

  return (
    <div className={`flex items-start p-4 rounded-lg border ${styles[type]} mb-4 relative`}>
      {/* ^^^ Check this opening tag for missing '>' ^^^ */}

      <Icon className="h-5 w-5 mt-0.5 mr-3 flex-shrink-0" />
      
      <div className="flex-1">
        {/* FIXED: Render title directly, do not wrap in extra {} */}
        {title && <h3 className="text-sm font-bold mb-1">{title}</h3>}
        {message && <div className="text-sm opacity-90">{message}</div>}
      </div>

      {onClose && (
        <button 
          onClick={onClose} 
          className="ml-3 hover:opacity-70 transition-opacity"
        >
          <X className="h-5 w-5" />
        </button>
      )}
    </div>
  );
};

export default Alert;