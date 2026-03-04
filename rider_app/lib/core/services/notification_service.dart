import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Service for handling local notifications
/// Sends alerts for triggers, movement detection, and payouts
class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin _notifications =
      FlutterLocalNotificationsPlugin();

  bool _initialized = false;
  bool _enabled = true;

  /// Initialize notification service
  Future<void> initialize() async {
    if (_initialized) return;

    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _notifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _onNotificationTapped,
    );

    // Load saved preference
    final prefs = await SharedPreferences.getInstance();
    _enabled = prefs.getBool('notifications_enabled') ?? true;

    _initialized = true;
  }

  void _onNotificationTapped(NotificationResponse response) {
    // Handle notification tap - could navigate to specific screen
    // For now, just log it
    print('Notification tapped: ${response.payload}');
  }

  /// Check if notifications are enabled
  bool get isEnabled => _enabled;

  /// Enable or disable notifications
  Future<void> setEnabled(bool enabled) async {
    _enabled = enabled;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('notifications_enabled', enabled);
  }

  /// Show a notification
  Future<void> show({
    required int id,
    required String title,
    required String body,
    String? payload,
    NotificationImportance importance = NotificationImportance.high,
  }) async {
    if (!_enabled) return;
    if (!_initialized) await initialize();

    final androidDetails = AndroidNotificationDetails(
      'auxilia_${importance.name}',
      importance == NotificationImportance.high
          ? 'Important Alerts'
          : 'General Updates',
      channelDescription: importance == NotificationImportance.high
          ? 'Critical alerts for triggers and payouts'
          : 'General app notifications',
      importance: importance == NotificationImportance.high
          ? Importance.high
          : Importance.defaultImportance,
      priority: importance == NotificationImportance.high
          ? Priority.high
          : Priority.defaultPriority,
      showWhen: true,
      icon: '@mipmap/ic_launcher',
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notifications.show(id, title, body, details, payload: payload);
  }

  // ============================================
  // Pre-built notification types for Auxilia
  // ============================================

  /// Movement detected - remind to enter delivery details
  Future<void> notifyMovementDetected() async {
    await show(
      id: 1001,
      title: 'Movement Detected',
      body:
          'Looks like you\'re traveling! Make sure to enter delivery details or you won\'t be eligible for claims.',
      payload: 'movement_detected',
      importance: NotificationImportance.high,
    );
  }

  /// High risk zone entered
  Future<void> notifyHighRiskZone(String zoneName, double riskLevel) async {
    await show(
      id: 1002,
      title: 'High Risk Zone Alert',
      body:
          'You\'ve entered $zoneName with ${(riskLevel * 100).toInt()}% risk level. Stay safe and drive carefully!',
      payload: 'high_risk_zone',
      importance: NotificationImportance.high,
    );
  }

  /// Weather alert
  Future<void> notifyWeatherAlert(String condition, String advice) async {
    await show(
      id: 1003,
      title: 'Weather Alert',
      body: '$condition - $advice',
      payload: 'weather_alert',
      importance: NotificationImportance.high,
    );
  }

  /// Traffic surge detected
  Future<void> notifyTrafficSurge(
    String zoneName,
    int congestionPercent,
  ) async {
    await show(
      id: 1004,
      title: 'Traffic Alert',
      body:
          '$congestionPercent% congestion in $zoneName. Consider alternate routes to avoid delays.',
      payload: 'traffic_surge',
      importance: NotificationImportance.normal,
    );
  }

  /// Trigger detected - potential claim
  Future<void> notifyTriggerDetected(String triggerType, String details) async {
    await show(
      id: 1005,
      title: 'Trigger Detected - Claim Eligible',
      body: '$triggerType: $details. You may file a claim for lost income.',
      payload: 'trigger_detected',
      importance: NotificationImportance.high,
    );
  }

  /// Claim status update
  Future<void> notifyClaimUpdate(String claimId, String status) async {
    String message;
    switch (status.toLowerCase()) {
      case 'approved':
        message = 'Your claim has been approved! Payout is being processed.';
        break;
      case 'paid':
        message =
            'Payout complete! Check your account for the credited amount.';
        break;
      case 'rejected':
        message = 'Your claim was not approved. Tap to view details.';
        break;
      default:
        message = 'Claim status updated to: $status';
    }

    await show(
      id: 1006,
      title: 'Claim Update',
      body: message,
      payload: 'claim_update:$claimId',
      importance: NotificationImportance.high,
    );
  }

  /// Policy expiring soon
  Future<void> notifyPolicyExpiring(int daysLeft) async {
    await show(
      id: 1007,
      title: 'Policy Expiring Soon',
      body:
          'Your policy expires in $daysLeft day${daysLeft > 1 ? 's' : ''}. Renew now to stay protected!',
      payload: 'policy_expiring',
      importance: NotificationImportance.high,
    );
  }

  /// Policy expired
  Future<void> notifyPolicyExpired() async {
    await show(
      id: 1008,
      title: 'Policy Expired',
      body:
          'Your coverage has expired. Renew now to reactivate protection and claim eligibility.',
      payload: 'policy_expired',
      importance: NotificationImportance.high,
    );
  }

  /// Test notification - for demo purposes
  Future<void> sendTestNotification() async {
    await show(
      id: 9999,
      title: 'Test Notification',
      body:
          'Notifications are working! You\'ll receive alerts for triggers, claims, and safety updates.',
      payload: 'test',
      importance: NotificationImportance.high,
    );
  }
}

enum NotificationImportance { high, normal, low }
