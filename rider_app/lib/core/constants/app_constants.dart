/// API configuration constants
class ApiConstants {
  ApiConstants._();

  // Base URLs
  static const String baseUrl = 'http://20.244.41.25/api/v1';
  static const String productionUrl = 'https://api.auxilia.app/api/v1';

  // Endpoints
  static const String onboard = '/onboard';
  static const String riskScore = '/risk/score';
  static const String triggers = '/triggers';
  static const String claims = '/claims';
  static const String payout = '/payout';
  static const String policy = '/policy';

  // External APIs
  static const String weatherApi = 'https://api.openweathermap.org/data/2.5';
  static const String nominatimApi = 'https://nominatim.openstreetmap.org';

  // Timeouts
  static const int connectTimeout = 30000; // 30 seconds
  static const int receiveTimeout = 30000; // 30 seconds
}

/// App configuration constants
class AppConstants {
  AppConstants._();

  // Policy
  static const int basePremium = 99;
  static const int maxCoverage = 300;
  static const int policyDurationDays = 7;

  // Triggers
  static const double rainThreshold = 15.0; // mm/hr
  static const double tempThreshold = 42.0; // Celsius
  static const int aqiThreshold = 300;
  static const double activityDropThreshold = 0.30; // 30%

  // Zones
  static const Map<String, double> zoneMultipliers = {
    'Zone 1': 1.0,
    'Zone 2': 1.1,
    'Zone 3': 1.3,
    'Zone 4': 0.95,
    'Zone 5': 0.95,
    'Zone 6': 1.2,
    'Zone 7': 0.8,
  };

  // Animation durations
  static const Duration shortAnimation = Duration(milliseconds: 200);
  static const Duration mediumAnimation = Duration(milliseconds: 350);
  static const Duration longAnimation = Duration(milliseconds: 500);

  // Polling intervals
  static const Duration triggerPollInterval = Duration(minutes: 10);
  static const Duration statusRefreshInterval = Duration(minutes: 1);
}
