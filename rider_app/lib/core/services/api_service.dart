import 'package:dio/dio.dart';

import '../../../shared/models/models.dart';

class ApiConfig {
  // Use --dart-define API_BASE_URL=<url> to override at build time
  static const String productionUrl = 'https://auxila-api.sabarixr.me/api/v1';
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: productionUrl,
  );
  static const String localUrl = 'http://localhost:8000/api/v1';
  static const String emulatorUrl = 'http://10.0.2.2:8000/api/v1';
  static const String networkUrl = productionUrl;
  static const Duration timeout = Duration(seconds: 30);
}

class ApiResponse<T> {
  final bool success;
  final T? data;
  final String? error;

  ApiResponse({required this.success, this.data, this.error});

  factory ApiResponse.success(T data) => ApiResponse(success: true, data: data);

  factory ApiResponse.failure(String error) =>
      ApiResponse(success: false, error: error);
}

class ApiService {
  late final Dio _dio;
  final String baseUrl;

  ApiService({this.baseUrl = ApiConfig.baseUrl}) {
    _dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: ApiConfig.timeout,
        receiveTimeout: ApiConfig.timeout,
        headers: const {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );
  }

  void setAuthToken(String? token) {
    if (token == null || token.isEmpty) {
      _dio.options.headers.remove('Authorization');
      return;
    }
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  Future<ApiResponse<T>> get<T>(
    String endpoint,
    T Function(dynamic json) fromJson,
  ) async {
    try {
      final response = await _dio.get(endpoint);
      return ApiResponse.success(fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.failure(_handleError(e));
    } catch (e) {
      return ApiResponse.failure(e.toString());
    }
  }

  Future<ApiResponse<T>> post<T>(
    String endpoint,
    Map<String, dynamic> body,
    T Function(dynamic json) fromJson,
  ) async {
    try {
      final response = await _dio.post(endpoint, data: body);
      return ApiResponse.success(fromJson(response.data));
    } on DioException catch (e) {
      return ApiResponse.failure(_handleError(e));
    } catch (e) {
      return ApiResponse.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> postJson(
    String endpoint,
    Map<String, dynamic> body,
  ) async {
    final response = await _dio.post(endpoint, data: body);
    return response.data as Map<String, dynamic>;
  }

  String _handleError(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
        return 'Connection timeout. Please check your internet.';
      case DioExceptionType.receiveTimeout:
        return 'Server took too long to respond.';
      case DioExceptionType.badResponse:
        return e.response?.data['detail']?.toString() ??
            'Server error: ${e.response?.statusCode}';
      case DioExceptionType.connectionError:
        return 'Cannot connect to server. Is the backend running?';
      default:
        return e.message ?? 'Unknown error occurred';
    }
  }

  Future<ApiResponse<RiderAuthSession>> registerRider({
    required String name,
    required String phone,
    required String password,
    required String persona,
    required String zoneId,
    String? email,
  }) async {
    final normalizedPhone = phone.startsWith('+') ? phone : '+91$phone';
    return post(
      '/auth/rider/register',
      {
        'name': name,
        'phone': normalizedPhone,
        'password': password,
        'email': email,
        'persona': persona,
        'zone_id': zoneId,
      },
      (json) => RiderAuthSession.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResponse<RiderAuthSession>> loginRider({
    required String phone,
    required String password,
  }) async {
    final normalizedPhone = phone.startsWith('+') ? phone : '+91$phone';
    return post(
      '/auth/rider/login',
      {'phone': normalizedPhone, 'password': password},
      (json) => RiderAuthSession.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResponse<Rider>> getRiderById(String riderId) async {
    return get('/riders/$riderId', (json) => Rider.fromJson(json));
  }

  Future<ApiResponse<Map<String, dynamic>>> deliveryCheckIn({
    required String riderId,
    required double deliveryLat,
    required double deliveryLon,
    String? orderId,
    double? riderLat,
    double? riderLon,
  }) async {
    return post('/riders/$riderId/delivery-checkin', {
      'order_id': orderId,
      'delivery_latitude': deliveryLat,
      'delivery_longitude': deliveryLon,
      'rider_latitude': riderLat,
      'rider_longitude': riderLon,
    }, (json) => json as Map<String, dynamic>);
  }

  Future<ApiResponse<Map<String, dynamic>>> updateRiderLocation({
    required String riderId,
    required double latitude,
    required double longitude,
  }) async {
    return post(
      '/riders/$riderId/update-location?latitude=$latitude&longitude=$longitude',
      {'latitude': latitude, 'longitude': longitude},
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<List<DeliveryHistoryItem>>> getDeliveryHistory(
    String riderId, {
    int limit = 50,
  }) async {
    return get(
      '/riders/$riderId/delivery-history?limit=$limit',
      (json) => (json as List)
          .map(
            (item) =>
                DeliveryHistoryItem.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }

  Future<ApiResponse<List<PublicPayoutLogEntry>>> getPublicPayoutLog({
    int limit = 20,
  }) async {
    return get(
      '/claims/public-payout-log?limit=$limit',
      (json) => (((json as Map<String, dynamic>)['payouts'] ?? []) as List)
          .map(
            (item) =>
                PublicPayoutLogEntry.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> getTrustRules() async {
    return get(
      '/policies/trust-rules/public',
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> getOfferWindow(
    String zoneId,
  ) async {
    return get(
      '/policies/offer-window/public?zone_id=$zoneId',
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> getQuotePreview({
    required String zoneId,
    required String persona,
    int durationDays = 7,
  }) async {
    return get(
      '/policies/quote-preview/public?zone_id=$zoneId&persona=$persona&duration_days=$durationDays',
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<List<Zone>>> getZones() async {
    return get(
      '/zones/',
      (json) => (json as List)
          .map((zone) => Zone.fromJson(zone as Map<String, dynamic>))
          .toList(),
    );
  }

  Future<ApiResponse<Zone>> getZoneById(String zoneId) async {
    return get('/zones/$zoneId', (json) => Zone.fromJson(json));
  }

  Future<ApiResponse<List<Policy>>> getRiderPolicies(String riderId) async {
    return get(
      '/policies/?rider_id=$riderId',
      (json) => (json as List)
          .map((policy) => Policy.fromJson(policy as Map<String, dynamic>))
          .toList(),
    );
  }

  Future<ApiResponse<Policy>> getActivePolicy(String riderId) async {
    final response = await getRiderPolicies(riderId);
    if (!response.success || response.data == null) {
      return ApiResponse.failure(response.error ?? 'Failed to load policies');
    }

    final activePolicies =
        response.data!.where((policy) => policy.isActive).toList()
          ..sort((a, b) => b.createdAt.compareTo(a.createdAt));

    if (activePolicies.isEmpty) {
      return ApiResponse.failure('No active policy found');
    }

    return ApiResponse.success(activePolicies.first);
  }

  Future<ApiResponse<Policy>> getLatestPolicy(String riderId) async {
    final response = await getRiderPolicies(riderId);
    if (!response.success || response.data == null) {
      return ApiResponse.failure(response.error ?? 'Failed to load policies');
    }

    final policies = response.data!
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    if (policies.isEmpty) {
      return ApiResponse.failure('No policy found');
    }

    return ApiResponse.success(policies.first);
  }

  Future<ApiResponse<Policy>> createPolicy({
    required String riderId,
    required String zoneId,
    required String persona,
  }) async {
    return post('/policies/', {
      'rider_id': riderId,
      'zone_id': zoneId,
      'persona': persona,
      'duration_days': 7,
    }, (json) => Policy.fromJson(json as Map<String, dynamic>));
  }

  Future<ApiResponse<Map<String, dynamic>>> renewPolicy({
    required String policyId,
    int durationWeeks = 1,
  }) async {
    return post(
      '/policies/$policyId/renew?duration_days=${durationWeeks * 7}',
      {},
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> upgradePolicy({
    required String policyId,
    required int additionalWeeks,
  }) async {
    // Upgrade is same as renew with more weeks
    return post('/policies/$policyId/renew', {
      'duration_days': additionalWeeks * 7,
    }, (json) => json as Map<String, dynamic>);
  }

  Future<ApiResponse<List<Claim>>> getRiderClaims(String riderId) async {
    return get(
      '/claims/?rider_id=$riderId',
      (json) => (json as List)
          .map((claim) => Claim.fromJson(claim as Map<String, dynamic>))
          .toList(),
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> runTriggerCheck() async {
    return post('/triggers/check', {}, (json) => json as Map<String, dynamic>);
  }

  Future<ApiResponse<Claim>> createClaim({
    required String policyId,
    required String triggerType,
  }) async {
    return post('/claims/', {
      'policy_id': policyId,
      'trigger_type': triggerType,
    }, (json) => Claim.fromJson(json as Map<String, dynamic>));
  }

  Future<ApiResponse<Map<String, dynamic>>> getClaimsSummary(
    String riderId,
  ) async {
    final response = await getRiderClaims(riderId);
    if (!response.success || response.data == null) {
      return ApiResponse.failure(response.error ?? 'Failed to load claims');
    }

    final claims = response.data!;
    final approvedClaims = claims.where((claim) => claim.isApproved).toList();
    final paidClaims = claims.where((claim) => claim.isPaid).toList();
    final protectedClaims = approvedClaims.isNotEmpty
        ? approvedClaims
        : paidClaims;

    return ApiResponse.success({
      'total': claims.length,
      'approved': approvedClaims.length,
      'paid': paidClaims.length,
      'settled': approvedClaims.length,
      'amount': protectedClaims.fold<double>(
        0,
        (sum, claim) => sum + claim.amount,
      ),
    });
  }

  Future<ApiResponse<Map<String, dynamic>>> createPolicyPaymentOrder({
    required String flowType,
    String? riderId,
    String? zoneId,
    String? persona,
    int durationDays = 7,
    String? existingPolicyId,
    int pointsToRedeem = 0,
  }) async {
    return post('/payments/policy-order', {
      'flow_type': flowType,
      'rider_id': riderId,
      'zone_id': zoneId,
      'persona': persona,
      'duration_days': durationDays,
      'existing_policy_id': existingPolicyId,
      'points_to_redeem': pointsToRedeem,
    }, (json) => json as Map<String, dynamic>);
  }

  Future<ApiResponse<Policy>> confirmPolicyPayment({
    required String flowType,
    required String orderId,
    required String paymentId,
    String? signature,
    String? riderId,
    String? zoneId,
    String? persona,
    int durationDays = 7,
    String? existingPolicyId,
    int pointsToRedeem = 0,
  }) async {
    return post(
      '/payments/policy-confirm',
      {
        'flow_type': flowType,
        'order_id': orderId,
        'payment_id': paymentId,
        'signature': signature,
        'rider_id': riderId,
        'zone_id': zoneId,
        'persona': persona,
        'duration_days': durationDays,
        'existing_policy_id': existingPolicyId,
        'points_to_redeem': pointsToRedeem,
      },
      (json) => Policy.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResponse<WeatherData>> getZoneWeather(
    String zoneId, {
    double? lat,
    double? lon,
  }) async {
    final query = (lat != null && lon != null) ? '?lat=$lat&lon=$lon' : '';
    return get(
      '/triggers/weather/$zoneId$query',
      (json) => WeatherData.fromJson(
        (json as Map<String, dynamic>)['current'] as Map<String, dynamic>,
      ),
    );
  }

  Future<ApiResponse<List<TriggerStatusModel>>> getZoneTriggers(
    String zoneId, {
    double? lat,
    double? lon,
  }) async {
    final query = (lat != null && lon != null) ? '?lat=$lat&lon=$lon' : '';
    return get(
      '/triggers/status/$zoneId$query',
      (json) => (((json as Map<String, dynamic>)['triggers'] ?? []) as List)
          .map(
            (trigger) =>
                TriggerStatusModel.fromJson(trigger as Map<String, dynamic>),
          )
          .toList(),
    );
  }

  Future<ApiResponse<DashboardStats>> getDashboardStats() async {
    return get('/dashboard/stats', (json) => DashboardStats.fromJson(json));
  }

  Future<ApiResponse<Map<String, dynamic>>> getArchitecture() async {
    return get(
      '/dashboard/architecture',
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> getZoneHeatmap({
    String? city,
  }) async {
    final query = city == null ? '' : '?city=$city';
    return get(
      '/dashboard/zone-heatmap$query',
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> getZoneNews(
    String zoneId, {
    double? lat,
    double? lon,
  }) async {
    final query = (lat != null && lon != null) ? '?lat=$lat&lon=$lon' : '';
    return get(
      '/triggers/news/$zoneId$query',
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> getZoneTraffic(
    String zoneId, {
    double? lat,
    double? lon,
  }) async {
    final query = (lat != null && lon != null) ? '?lat=$lat&lon=$lon' : '';
    return get(
      '/triggers/traffic/$zoneId$query',
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> getZoneSurge(
    String zoneId, {
    double? lat,
    double? lon,
  }) async {
    final query = (lat != null && lon != null) ? '?lat=$lat&lon=$lon' : '';
    return get(
      '/triggers/surge/$zoneId$query',
      (json) => json as Map<String, dynamic>,
    );
  }

  Future<ApiResponse<Map<String, dynamic>>> getSystemAlerts() async {
    return get('/dashboard/alerts', (json) => json as Map<String, dynamic>);
  }

  Future<ApiResponse<List<Claim>>> getRiderClaimHistory(String riderId) async {
    return get(
      '/claims/?rider_id=$riderId&limit=50',
      (json) => (json as List)
          .map((claim) => Claim.fromJson(claim as Map<String, dynamic>))
          .toList(),
    );
  }

  Future<bool> healthCheck() async {
    try {
      final uri = Uri.parse(baseUrl.replaceFirst('/api/v1', '') + '/health');
      final response = await _dio.getUri(uri);
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  void dispose() {
    _dio.close(force: true);
  }
}

final apiService = ApiService();
