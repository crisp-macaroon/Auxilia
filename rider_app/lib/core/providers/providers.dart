import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:geolocator/geolocator.dart';
import '../services/api_service.dart';
import '../../shared/models/models.dart';

/// API Service provider
final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService();
});

/// Shared preferences provider
final sharedPreferencesProvider = FutureProvider<SharedPreferences>((
  ref,
) async {
  return await SharedPreferences.getInstance();
});

/// Current rider ID from local storage
final currentRiderIdProvider = FutureProvider<String?>((ref) async {
  final prefs = await ref.watch(sharedPreferencesProvider.future);
  return prefs.getString('rider_id');
});

/// Current rider provider
final currentRiderProvider = FutureProvider<Rider?>((ref) async {
  final riderId = await ref.watch(currentRiderIdProvider.future);
  if (riderId == null) return null;

  final api = ref.watch(apiServiceProvider);
  final response = await api.getRiderById(riderId);

  if (response.success && response.data != null) {
    return response.data;
  }
  return null;
});

/// Zones list provider
final zonesProvider = FutureProvider<List<Zone>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  final response = await api.getZones();

  if (response.success && response.data != null) {
    return response.data!;
  }
  return [];
});

/// Active policy provider for current rider
final activePolicyProvider = FutureProvider<Policy?>((ref) async {
  final riderId = await ref.watch(currentRiderIdProvider.future);
  if (riderId == null) return null;

  final api = ref.watch(apiServiceProvider);
  final response = await api.getActivePolicy(riderId);

  if (response.success && response.data != null) {
    return response.data;
  }
  return null;
});

/// Claims list provider for current rider
final claimsProvider = FutureProvider<List<Claim>>((ref) async {
  final riderId = await ref.watch(currentRiderIdProvider.future);
  if (riderId == null) return [];

  final api = ref.watch(apiServiceProvider);
  final response = await api.getRiderClaims(riderId);

  if (response.success && response.data != null) {
    return response.data!;
  }
  return [];
});

/// Claims summary provider
final claimsSummaryProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final riderId = await ref.watch(currentRiderIdProvider.future);
  if (riderId == null) return {'total': 0, 'amount': 0};

  final api = ref.watch(apiServiceProvider);
  final response = await api.getClaimsSummary(riderId);

  if (response.success && response.data != null) {
    return response.data!;
  }
  return {'total': 0, 'amount': 0};
});

/// Weather data provider for current zone
final weatherProvider = FutureProvider<WeatherData?>((ref) async {
  final policy = await ref.watch(activePolicyProvider.future);
  if (policy == null) return null;

  final api = ref.watch(apiServiceProvider);
  final response = await api.getZoneWeather(policy.zoneId);

  if (response.success && response.data != null) {
    return response.data;
  }
  return null;
});

/// Active triggers for current zone
final triggersProvider = FutureProvider<List<TriggerStatusModel>>((ref) async {
  final policy = await ref.watch(activePolicyProvider.future);
  if (policy == null) return [];

  final api = ref.watch(apiServiceProvider);
  final response = await api.getZoneTriggers(policy.zoneId);

  if (response.success && response.data != null) {
    return response.data!;
  }
  return [];
});

/// Dashboard stats provider
final dashboardStatsProvider = FutureProvider<DashboardStats?>((ref) async {
  final api = ref.watch(apiServiceProvider);
  final response = await api.getDashboardStats();

  if (response.success && response.data != null) {
    return response.data;
  }
  return null;
});

/// Onboarding state notifier
class OnboardingState {
  final String? name;
  final String? phone;
  final String? email;
  final String? persona;
  final String? zoneId;
  final Zone? selectedZone;

  OnboardingState({
    this.name,
    this.phone,
    this.email,
    this.persona,
    this.zoneId,
    this.selectedZone,
  });

  OnboardingState copyWith({
    String? name,
    String? phone,
    String? email,
    String? persona,
    String? zoneId,
    Zone? selectedZone,
  }) {
    return OnboardingState(
      name: name ?? this.name,
      phone: phone ?? this.phone,
      email: email ?? this.email,
      persona: persona ?? this.persona,
      zoneId: zoneId ?? this.zoneId,
      selectedZone: selectedZone ?? this.selectedZone,
    );
  }

  bool get isComplete =>
      name != null && phone != null && persona != null && zoneId != null;
}

class OnboardingNotifier extends StateNotifier<OnboardingState> {
  final ApiService _api;
  final Ref _ref;

  OnboardingNotifier(this._api, this._ref) : super(OnboardingState());

  void setPersona(String persona) {
    state = state.copyWith(persona: persona);
  }

  void setProfile({
    required String name,
    required String phone,
    String? email,
  }) {
    state = state.copyWith(name: name, phone: phone, email: email);
  }

  void setZone(Zone zone) {
    state = state.copyWith(zoneId: zone.id, selectedZone: zone);
  }

  Future<ApiResponse<Rider>> register() async {
    if (!state.isComplete) {
      return ApiResponse.failure('Incomplete registration data');
    }

    final response = await _api.registerRider(
      name: state.name!,
      phone: state.phone!,
      persona: state.persona!,
      zoneId: state.zoneId!,
      email: state.email,
    );

    if (response.success && response.data != null) {
      // Save rider ID to local storage
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('rider_id', response.data!.id);

      // Refresh the current rider provider
      _ref.invalidate(currentRiderIdProvider);
      _ref.invalidate(currentRiderProvider);
    }

    return response;
  }

  void reset() {
    state = OnboardingState();
  }
}

final onboardingProvider =
    StateNotifierProvider<OnboardingNotifier, OnboardingState>((ref) {
      final api = ref.watch(apiServiceProvider);
      return OnboardingNotifier(api, ref);
    });

/// Helper to check if backend is connected
final backendConnectedProvider = FutureProvider<bool>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.healthCheck();
});

final locationTrackingProvider = StreamProvider<Position>((ref) async* {
  // First check if location service is enabled
  final enabled = await Geolocator.isLocationServiceEnabled();
  if (!enabled) {
    // Try to open location settings
    await Geolocator.openLocationSettings();
    // Re-check after user interaction
    final stillDisabled = !await Geolocator.isLocationServiceEnabled();
    if (stillDisabled) {
      throw Exception('Location services are disabled. Please enable GPS.');
    }
  }

  // Request permission
  var permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
  }

  if (permission == LocationPermission.deniedForever) {
    // Open app settings so user can enable permission
    await Geolocator.openAppSettings();
    throw Exception(
      'Location permission permanently denied. Please enable in Settings.',
    );
  }

  if (permission == LocationPermission.denied) {
    throw Exception('Location permission denied. Tap to enable.');
  }

  // Get initial position first
  final initialPosition = await Geolocator.getCurrentPosition(
    desiredAccuracy: LocationAccuracy.high,
  );
  yield initialPosition;

  // Then stream updates
  yield* Geolocator.getPositionStream(
    locationSettings: const LocationSettings(
      accuracy: LocationAccuracy.high,
      distanceFilter: 50,
    ),
  );
});

final architectureProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  final response = await api.getArchitecture();
  if (response.success && response.data != null) return response.data!;
  return {'architecture': {}, 'pipeline': []};
});

final zoneHeatmapProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  final response = await api.getZoneHeatmap();
  if (response.success && response.data != null) return response.data!;
  return {'points': [], 'count': 0};
});

/// Zone news provider - Gemini-powered incident analysis
final zoneNewsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final policy = await ref.watch(activePolicyProvider.future);
  if (policy == null) return {'incidents': [], 'incident_count': 0};

  final api = ref.watch(apiServiceProvider);
  final response = await api.getZoneNews(policy.zoneId);
  if (response.success && response.data != null) return response.data!;
  return {'incidents': [], 'incident_count': 0};
});

/// Zone traffic provider
final zoneTrafficProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final policy = await ref.watch(activePolicyProvider.future);
  if (policy == null) return {};

  final api = ref.watch(apiServiceProvider);
  final response = await api.getZoneTraffic(policy.zoneId);
  if (response.success && response.data != null) return response.data!;
  return {};
});

/// Zone surge provider
final zoneSurgeProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final policy = await ref.watch(activePolicyProvider.future);
  if (policy == null) return {};

  final api = ref.watch(apiServiceProvider);
  final response = await api.getZoneSurge(policy.zoneId);
  if (response.success && response.data != null) return response.data!;
  return {};
});

/// System alerts provider
final systemAlertsProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  final response = await api.getSystemAlerts();
  if (response.success && response.data != null) return response.data!;
  return {'alerts': [], 'count': 0};
});

/// Claim history provider
final claimHistoryProvider = FutureProvider<List<Claim>>((ref) async {
  final riderId = await ref.watch(currentRiderIdProvider.future);
  if (riderId == null) return [];

  final api = ref.watch(apiServiceProvider);
  final response = await api.getRiderClaimHistory(riderId);
  if (response.success && response.data != null) return response.data!;
  return [];
});
