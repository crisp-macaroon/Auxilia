import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'notification_service.dart';

@pragma('vm:entry-point')
Future<void> fcmBackgroundHandler(RemoteMessage message) async {
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Ignore when Firebase config files are not present in local setup.
  }
}

class FcmService {
  FcmService._();

  static final FcmService instance = FcmService._();
  static const _topicKey = 'fcm_topic';

  final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) {
      return;
    }

    try {
      await Firebase.initializeApp();
    } catch (_) {
      // App remains usable even without Firebase files in local dev.
      return;
    }

    final settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    if (settings.authorizationStatus == AuthorizationStatus.denied) {
      _initialized = true;
      return;
    }

    FirebaseMessaging.onBackgroundMessage(fcmBackgroundHandler);

    final local = NotificationService();
    await local.initialize();

    FirebaseMessaging.onMessage.listen((message) async {
      final title = message.notification?.title ?? 'Auxilia Alert';
      final body =
          message.notification?.body ??
          message.data['message']?.toString() ??
          '';
      if (body.isNotEmpty) {
        await local.show(
          id:
              message.messageId?.hashCode ??
              DateTime.now().millisecondsSinceEpoch,
          title: title,
          body: body,
          payload: 'fcm_foreground',
          importance: NotificationImportance.high,
        );
      }
    });

    FirebaseMessaging.onMessageOpenedApp.listen((message) {
      debugPrint('Opened from notification: ${message.messageId}');
    });

    final token = await _messaging.getToken();
    if (token != null) {
      debugPrint('FCM token: $token');
    }

    _initialized = true;

    await syncStoredTopic();
  }

  Future<void> syncStoredTopic() async {
    await initialize();
    if (!_initialized) {
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final phone = prefs.getString('rider_phone');
    if (phone != null && phone.isNotEmpty) {
      await syncTopicForPhone(phone);
    }
  }

  String topicForPhone(String phone) {
    final digits = phone.replaceAll(RegExp(r'\D'), '');
    if (digits.isEmpty) {
      return 'rider_unknown';
    }
    return 'rider_$digits';
  }

  Future<void> syncTopicForPhone(String phone) async {
    await initialize();
    if (!_initialized) {
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final nextTopic = topicForPhone(phone);
    final previousTopic = prefs.getString(_topicKey);

    if (previousTopic != null && previousTopic != nextTopic) {
      await _messaging.unsubscribeFromTopic(previousTopic);
    }

    if (previousTopic != nextTopic) {
      await _messaging.subscribeToTopic(nextTopic);
      await prefs.setString(_topicKey, nextTopic);
      debugPrint('Subscribed to topic: $nextTopic');
    }
  }

  Future<void> clearTopicSubscription() async {
    await initialize();
    if (!_initialized) {
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    final previousTopic = prefs.getString(_topicKey);
    if (previousTopic != null) {
      await _messaging.unsubscribeFromTopic(previousTopic);
      await prefs.remove(_topicKey);
      debugPrint('Unsubscribed from topic: $previousTopic');
    }
  }
}
