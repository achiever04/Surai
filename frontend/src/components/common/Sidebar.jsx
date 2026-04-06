import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Camera,
  Users,
  FileText,
  BarChart2,
  Shield,
  Bell,
  Settings
} from 'lucide-react';

const Sidebar = () => {
  const location = useLocation();

  // FIXED: Defined the complete menu items list
  const menuItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/alerts', label: 'Alerts', icon: Bell },
    { path: '/cameras', label: 'Live Feeds', icon: Camera },
    { path: '/watchlist', label: 'Watchlist', icon: Users },
    { path: '/evidence', label: 'Evidence', icon: FileText },
    { path: '/analytics', label: 'Analytics', icon: BarChart2 },
    { path: '/audit', label: 'Audit Logs', icon: Shield },
    { path: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="h-screen w-64 bg-gray-900 dark:bg-gray-950 text-white flex flex-col flex-shrink-0 transition-all duration-300">
      {/* Brand Logo Area */}
      <div className="h-16 flex items-center px-6 border-b border-gray-800">
        <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
          <Camera className="h-5 w-5 text-white" />
        </div>
        <span className="text-xl font-bold tracking-wider">Surveillance AI</span>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 group ${isActive
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
            >
              <Icon size={20} className={isActive ? 'text-white' : 'text-gray-400 group-hover:text-white'} />
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer / User Info */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 rounded-full bg-gray-700 flex items-center justify-center text-xs font-bold">
            AD
          </div>
          <div>
            <p className="text-sm font-medium text-white">Admin User</p>
            <p className="text-xs text-gray-500">System Administrator</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;