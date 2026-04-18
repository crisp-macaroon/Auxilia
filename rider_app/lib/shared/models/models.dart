/// Rider model
class Rider {
  final String id;
  final String name;
  final String phone;
  final String? email;
  final String persona;
  final String zoneId;
  final double? latitude;
  final double? longitude;
  final double riskScore;
  final int loyaltyPoints;
  final String status;
  final DateTime createdAt;

  Rider({
    required this.id,
    required this.name,
    required this.phone,
    this.email,
    required this.persona,
    required this.zoneId,
    this.latitude,
    this.longitude,
    required this.riskScore,
    required this.loyaltyPoints,
    required this.status,
    required this.createdAt,
  });

  factory Rider.fromJson(Map<String, dynamic> json) {
    return Rider(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      phone: json['phone'] ?? '',
      email: json['email'],
      persona: json['persona'] ?? 'food_delivery',
      zoneId: json['zone_id'] ?? '',
      latitude: json['latitude']?.toDouble(),
      longitude: json['longitude']?.toDouble(),
      riskScore: (json['risk_score'] ?? 0.5).toDouble(),
      loyaltyPoints: (json['loyalty_points'] ?? 0) as int,
      status: json['status'] ?? 'active',
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'phone': phone,
      'email': email,
      'persona': persona,
      'zone_id': zoneId,
      'latitude': latitude,
      'longitude': longitude,
      'risk_score': riskScore,
      'status': status,
    };
  }
}

class RiderAuthSession {
  final String accessToken;
  final String tokenType;
  final int expiresIn;
  final Rider rider;

  RiderAuthSession({
    required this.accessToken,
    required this.tokenType,
    required this.expiresIn,
    required this.rider,
  });

  factory RiderAuthSession.fromJson(Map<String, dynamic> json) {
    return RiderAuthSession(
      accessToken: json['access_token'] ?? '',
      tokenType: json['token_type'] ?? 'bearer',
      expiresIn: json['expires_in'] ?? 0,
      rider: Rider.fromJson(json['rider'] as Map<String, dynamic>),
    );
  }
}

/// Zone model
class Zone {
  final String id;
  final String name;
  final String city;
  final String? state;
  final String country;
  final double latitude;
  final double longitude;
  final double radiusKm;
  final String riskLevel;
  final double basePremiumFactor;
  final bool isActive;

  Zone({
    required this.id,
    required this.name,
    required this.city,
    this.state,
    required this.country,
    required this.latitude,
    required this.longitude,
    required this.radiusKm,
    required this.riskLevel,
    required this.basePremiumFactor,
    required this.isActive,
  });

  factory Zone.fromJson(Map<String, dynamic> json) {
    return Zone(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      city: json['city'] ?? '',
      state: json['state'],
      country: json['country'] ?? 'IN',
      latitude: (json['latitude'] ?? 0).toDouble(),
      longitude: (json['longitude'] ?? 0).toDouble(),
      radiusKm: (json['radius_km'] ?? 2.5).toDouble(),
      riskLevel: json['risk_level'] ?? 'medium',
      basePremiumFactor: (json['base_premium_factor'] ?? 1.0).toDouble(),
      isActive: json['is_active'] ?? true,
    );
  }
}

/// Policy model
class Policy {
  final String id;
  final String riderId;
  final String zoneId;
  final String persona;
  final double premium;
  final double coverage;
  final DateTime startDate;
  final DateTime endDate;
  final String status;
  final String? txHash;
  final DateTime createdAt;

  Policy({
    required this.id,
    required this.riderId,
    required this.zoneId,
    required this.persona,
    required this.premium,
    required this.coverage,
    required this.startDate,
    required this.endDate,
    required this.status,
    this.txHash,
    required this.createdAt,
  });

  factory Policy.fromJson(Map<String, dynamic> json) {
    final rawStatus = (json['status'] ?? 'active').toString();
    return Policy(
      id: json['id'] ?? '',
      riderId: json['rider_id'] ?? '',
      zoneId: json['zone_id'] ?? '',
      persona: json['persona'] ?? 'food_delivery',
      premium: (json['premium'] ?? 0).toDouble(),
      coverage: (json['coverage'] ?? 0).toDouble(),
      startDate: json['start_date'] != null
          ? DateTime.parse(json['start_date'])
          : DateTime.now(),
      endDate: json['end_date'] != null
          ? DateTime.parse(json['end_date'])
          : DateTime.now().add(const Duration(days: 7)),
      status: rawStatus.toLowerCase(),
      txHash: json['tx_hash'],
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  }

  int get daysRemaining {
    final now = DateTime.now();
    final diff = endDate.difference(now).inDays;
    return diff > 0 ? diff : 0;
  }

  bool get isActive =>
      status.toLowerCase() == 'active' && endDate.isAfter(DateTime.now());
}

/// Claim model
class Claim {
  final String id;
  final String policyId;
  final String riderId;
  final String triggerType;
  final double triggerValue;
  final double threshold;
  final double amount;
  final String status;
  final double fraudScore;
  final String? aiDecision;
  final String? txHash;
  final DateTime createdAt;
  final DateTime? processedAt;

  Claim({
    required this.id,
    required this.policyId,
    required this.riderId,
    required this.triggerType,
    required this.triggerValue,
    required this.threshold,
    required this.amount,
    required this.status,
    required this.fraudScore,
    this.aiDecision,
    this.txHash,
    required this.createdAt,
    this.processedAt,
  });

  factory Claim.fromJson(Map<String, dynamic> json) {
    return Claim(
      id: json['id'] ?? '',
      policyId: json['policy_id'] ?? '',
      riderId: json['rider_id'] ?? '',
      triggerType: json['trigger_type'] ?? 'rain',
      triggerValue: (json['trigger_value'] ?? 0).toDouble(),
      threshold: (json['threshold'] ?? 0).toDouble(),
      amount: (json['amount'] ?? 0).toDouble(),
      status: json['status'] ?? 'pending',
      fraudScore: (json['fraud_score'] ?? 0).toDouble(),
      aiDecision: json['ai_decision'],
      txHash: json['tx_hash'],
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      processedAt: json['processed_at'] != null
          ? DateTime.parse(json['processed_at'])
          : null,
    );
  }

  bool get isPaid => status == 'paid';
  bool get isApproved => status == 'approved' || status == 'paid';
}

/// Trigger event model
class TriggerEvent {
  final String id;
  final String zoneId;
  final String triggerType;
  final double value;
  final double threshold;
  final bool isActive;
  final String? source;
  final DateTime createdAt;
  final DateTime? expiresAt;

  TriggerEvent({
    required this.id,
    required this.zoneId,
    required this.triggerType,
    required this.value,
    required this.threshold,
    required this.isActive,
    this.source,
    required this.createdAt,
    this.expiresAt,
  });

  factory TriggerEvent.fromJson(Map<String, dynamic> json) {
    return TriggerEvent(
      id: json['id'] ?? '',
      zoneId: json['zone_id'] ?? '',
      triggerType: json['trigger_type'] ?? 'rain',
      value: (json['value'] ?? 0).toDouble(),
      threshold: (json['threshold'] ?? 0).toDouble(),
      isActive: json['is_active'] ?? false,
      source: json['source'],
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'])
          : null,
    );
  }

  String get statusLabel {
    if (!isActive) return 'OK';
    if (value >= threshold * 0.8) return 'WATCH';
    if (value >= threshold) return 'TRIGGERED';
    return 'OK';
  }
}

class TriggerStatusModel {
  final String zoneId;
  final String zoneName;
  final String triggerType;
  final double currentValue;
  final double threshold;
  final bool isActive;
  final int affectedPolicies;
  final DateTime lastUpdated;
  final String source;

  TriggerStatusModel({
    required this.zoneId,
    required this.zoneName,
    required this.triggerType,
    required this.currentValue,
    required this.threshold,
    required this.isActive,
    required this.affectedPolicies,
    required this.lastUpdated,
    required this.source,
  });

  factory TriggerStatusModel.fromJson(Map<String, dynamic> json) {
    return TriggerStatusModel(
      zoneId: json['zone_id'] ?? '',
      zoneName: json['zone_name'] ?? '',
      triggerType: json['trigger_type'] ?? 'rain',
      currentValue: (json['current_value'] ?? 0).toDouble(),
      threshold: (json['threshold'] ?? 0).toDouble(),
      isActive: json['is_active'] ?? false,
      affectedPolicies: json['affected_policies'] ?? 0,
      lastUpdated: json['last_updated'] != null
          ? DateTime.parse(json['last_updated'])
          : DateTime.now(),
      source: json['source'] ?? '',
    );
  }

  String get statusLabel => isActive ? 'TRIGGERED' : 'OK';
}

class DeliveryHistoryItem {
  final String id;
  final String riderId;
  final String? orderId;
  final String assignedZoneId;
  final String? assignedZoneName;
  final double deliveryLatitude;
  final double deliveryLongitude;
  final bool isDeliveryInCoverageZone;
  final String eligibilityReason;
  final double computedRiskScore;
  final double weatherRisk;
  final double trafficRisk;
  final double incidentRisk;
  final DateTime? assessedAt;
  final DateTime createdAt;

  DeliveryHistoryItem({
    required this.id,
    required this.riderId,
    this.orderId,
    required this.assignedZoneId,
    this.assignedZoneName,
    required this.deliveryLatitude,
    required this.deliveryLongitude,
    required this.isDeliveryInCoverageZone,
    required this.eligibilityReason,
    required this.computedRiskScore,
    required this.weatherRisk,
    required this.trafficRisk,
    required this.incidentRisk,
    this.assessedAt,
    required this.createdAt,
  });

  factory DeliveryHistoryItem.fromJson(Map<String, dynamic> json) {
    return DeliveryHistoryItem(
      id: json['id'] ?? '',
      riderId: json['rider_id'] ?? '',
      orderId: json['order_id'],
      assignedZoneId: json['assigned_zone_id'] ?? '',
      assignedZoneName: json['assigned_zone_name'],
      deliveryLatitude: (json['delivery_latitude'] ?? 0).toDouble(),
      deliveryLongitude: (json['delivery_longitude'] ?? 0).toDouble(),
      isDeliveryInCoverageZone: json['is_delivery_in_coverage_zone'] ?? false,
      eligibilityReason: json['eligibility_reason'] ?? '',
      computedRiskScore: (json['computed_risk_score'] ?? 0).toDouble(),
      weatherRisk: (json['weather_risk'] ?? 0).toDouble(),
      trafficRisk: (json['traffic_risk'] ?? 0).toDouble(),
      incidentRisk: (json['incident_risk'] ?? 0).toDouble(),
      assessedAt: json['assessed_at'] != null
          ? DateTime.parse(json['assessed_at'])
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'])
          : DateTime.now(),
    );
  }
}

class PublicPayoutLogEntry {
  final String claimId;
  final String rider;
  final String triggerType;
  final double triggerValue;
  final double threshold;
  final double payoutAmount;
  final String? zone;
  final String? txHash;
  final DateTime processedAt;

  PublicPayoutLogEntry({
    required this.claimId,
    required this.rider,
    required this.triggerType,
    required this.triggerValue,
    required this.threshold,
    required this.payoutAmount,
    this.zone,
    this.txHash,
    required this.processedAt,
  });

  factory PublicPayoutLogEntry.fromJson(Map<String, dynamic> json) {
    return PublicPayoutLogEntry(
      claimId: json['claim_id'] ?? '',
      rider: json['rider'] ?? 'Rider',
      triggerType: json['trigger_type'] ?? 'unknown',
      triggerValue: (json['trigger_value'] ?? 0).toDouble(),
      threshold: (json['threshold'] ?? 0).toDouble(),
      payoutAmount: (json['payout_amount'] ?? 0).toDouble(),
      zone: json['zone'],
      txHash: json['tx_hash'],
      processedAt: json['processed_at'] != null
          ? DateTime.parse(json['processed_at'])
          : DateTime.now(),
    );
  }
}

/// Weather data model
class WeatherData {
  final String zoneId;
  final double temperature;
  final double feelsLike;
  final double humidity;
  final double rainfallOneHour;
  final double rainfallThreeHours;
  final double windSpeed;
  final String condition;
  final String description;
  final DateTime timestamp;

  WeatherData({
    required this.zoneId,
    required this.temperature,
    required this.feelsLike,
    required this.humidity,
    required this.rainfallOneHour,
    required this.rainfallThreeHours,
    required this.windSpeed,
    required this.condition,
    required this.description,
    required this.timestamp,
  });

  factory WeatherData.fromJson(Map<String, dynamic> json) {
    return WeatherData(
      zoneId: json['zone_id'] ?? '',
      temperature: (json['temperature'] ?? 0).toDouble(),
      feelsLike: (json['feels_like'] ?? 0).toDouble(),
      humidity: (json['humidity'] ?? 0).toDouble(),
      rainfallOneHour: (json['rain_1h'] ?? 0).toDouble(),
      rainfallThreeHours: (json['rain_3h'] ?? 0).toDouble(),
      windSpeed: (json['wind_speed'] ?? 0).toDouble(),
      condition: json['weather_main'] ?? 'Clear',
      description: json['weather_description'] ?? '',
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
    );
  }

  double get rainfall =>
      rainfallOneHour > 0 ? rainfallOneHour : rainfallThreeHours;
}

/// Dashboard stats model
class DashboardStats {
  final int totalPolicies;
  final int activePolicies;
  final int totalClaims;
  final int pendingClaims;
  final double totalPremiumCollected;
  final double totalClaimsPaid;
  final int activeRiders;
  final double avgRiskScore;
  final int activeTriggers;
  final double lossRatio;

  DashboardStats({
    required this.totalPolicies,
    required this.activePolicies,
    required this.totalClaims,
    required this.pendingClaims,
    required this.totalPremiumCollected,
    required this.totalClaimsPaid,
    required this.activeRiders,
    required this.avgRiskScore,
    required this.activeTriggers,
    required this.lossRatio,
  });

  factory DashboardStats.fromJson(Map<String, dynamic> json) {
    return DashboardStats(
      totalPolicies: json['total_policies'] ?? 0,
      activePolicies: json['active_policies'] ?? 0,
      totalClaims: json['total_claims'] ?? 0,
      pendingClaims: json['pending_claims'] ?? 0,
      totalPremiumCollected: (json['total_premium_collected'] ?? 0).toDouble(),
      totalClaimsPaid: (json['total_claims_paid'] ?? 0).toDouble(),
      activeRiders: json['active_riders'] ?? 0,
      avgRiskScore: (json['avg_risk_score'] ?? 0).toDouble(),
      activeTriggers: json['active_triggers'] ?? 0,
      lossRatio: (json['loss_ratio'] ?? 0).toDouble(),
    );
  }
}
