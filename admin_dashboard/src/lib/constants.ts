// API Configuration
const PROD_API_BASE_URL = 'https://auxila-api.sabarixr.me/api/v1';
const DEV_API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

const resolvedServerApiBaseUrl =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === 'production' ? PROD_API_BASE_URL : DEV_API_BASE_URL);

export const SERVER_API_BASE_URL = resolvedServerApiBaseUrl.replace(/\/$/, '');

export const API_BASE_URL = typeof window === 'undefined' ? SERVER_API_BASE_URL : '/api/v1';

// App Configuration
export const APP_NAME = 'Auxilia Admin';
export const APP_DESCRIPTION = 'AI-Powered Parametric Insurance Admin Dashboard';
export const DEPLOYMENT_PIPELINE_VERSION = '2026-03-20-reinit';

// Navigation Items
export const NAV_ITEMS = [
  { name: 'Dashboard', href: '/dashboard', icon: 'LayoutDashboard' },
  { name: 'Policies', href: '/policies', icon: 'FileText' },
  { name: 'Claims', href: '/claims', icon: 'ClipboardList' },
  { name: 'Riders', href: '/riders', icon: 'Users' },
  { name: 'Analytics', href: '/analytics', icon: 'BarChart3' },
  { name: 'Triggers', href: '/triggers', icon: 'Zap' },
  { name: 'Settings', href: '/settings', icon: 'Settings' },
] as const;

// Status Colors
export const STATUS_COLORS = {
  active: 'bg-green-100 text-green-800',
  pending: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-blue-100 text-blue-800',
  rejected: 'bg-red-100 text-red-800',
  expired: 'bg-gray-100 text-gray-800',
  processing: 'bg-purple-100 text-purple-800',
} as const;

// Trigger Types
export const TRIGGER_TYPES = {
  rain: { label: 'Heavy Rain', icon: 'CloudRain', color: 'blue' },
  traffic: { label: 'Traffic Jam', icon: 'Car', color: 'orange' },
  surge: { label: 'Low Demand', icon: 'TrendingUp', color: 'purple' },
  road_disruption: { label: 'Road Disruption', icon: 'AlertTriangle', color: 'red' },
} as const;

// Chart Colors
export const CHART_COLORS = {
  primary: '#FF6B35',
  secondary: '#4ECDC4',
  tertiary: '#45B7D1',
  quaternary: '#96CEB4',
  danger: '#EF4444',
  warning: '#F59E0B',
  success: '#10B981',
};

// Zones
export const MUMBAI_ZONES = [
  { id: 'andheri', name: 'Andheri', riskLevel: 'high' },
  { id: 'bandra', name: 'Bandra', riskLevel: 'medium' },
  { id: 'colaba', name: 'Colaba', riskLevel: 'low' },
  { id: 'dadar', name: 'Dadar', riskLevel: 'high' },
  { id: 'kurla', name: 'Kurla', riskLevel: 'medium' },
  { id: 'malad', name: 'Malad', riskLevel: 'medium' },
  { id: 'powai', name: 'Powai', riskLevel: 'low' },
  { id: 'thane', name: 'Thane', riskLevel: 'high' },
] as const;
