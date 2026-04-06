import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { User, LogOut, Menu } from 'lucide-react';
import NotificationCenter from './NotificationCenter';

const Header = () => {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 relative">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Left: Logo & Title */}
        <div className="flex items-center space-x-4">
          <button className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
            <Menu className="w-6 h-6 text-gray-600" />
          </button>
          <h1 className="text-xl font-bold text-gray-900">
            AI Surveillance Platform
          </h1>
        </div>

        {/* Right: Notifications + User */}
        <div className="flex items-center space-x-4">
          {/* Real-time Notification Center */}
          <NotificationCenter />

          {/* User Profile */}
          <div className="flex items-center space-x-3 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-700">
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              <User className="w-5 h-5 text-white" />
            </div>
            <div className="hidden md:block text-sm">
              <div className="font-medium text-gray-900">{user?.full_name}</div>
              <div className="text-gray-500 capitalize">{user?.role}</div>
            </div>
          </div>

          {/* Logout */}
          <button
            onClick={logout}
            className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/30 text-red-600"
            title="Logout"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;