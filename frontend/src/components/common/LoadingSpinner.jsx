import React from 'react';
import { Loader2 } from 'lucide-react'; // Assuming you use lucide-react

const LoadingSpinner = ({ message }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full w-full p-4">
      {/* ^^^ Check this opening tag ^^^ */}
      
      <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      
      {/* FIXED: Removed extra curly braces around message */}
      {message && (
        <p className="mt-2 text-gray-400 text-sm font-medium">
          {message}
        </p>
      )}
    </div>
  );
};

export default LoadingSpinner;