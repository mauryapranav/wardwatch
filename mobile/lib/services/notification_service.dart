/// WardWatch - FCM Notification Service (Step 4.3)
library;

import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';

/// Handles Firebase Cloud Messaging setup and token management.
class NotificationService {
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  /// Initialize FCM and request permission.
  Future<void> initialize() async {
    // Request permission (iOS requires explicit permission)
    final settings = await _messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('FCM permission granted.');
      await _saveToken();
    } else {
      debugPrint('FCM permission denied.');
    }

    // Handle token refresh
    _messaging.onTokenRefresh.listen(_saveFCMToken);

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Handle background/terminated message taps
    FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

    // Check for initial message (app opened from terminated state)
    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      _handleNotificationTap(initialMessage);
    }
  }

  /// Get the FCM token and save it to Firestore.
  Future<void> _saveToken() async {
    try {
      final token = await _messaging.getToken();
      if (token != null) {
        await _saveFCMToken(token);
      }
    } catch (e) {
      debugPrint('Failed to get FCM token: $e');
    }
  }

  /// Save FCM token to the user's Firestore profile.
  Future<void> _saveFCMToken(String token) async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) return;
      await _firestore.collection('users').doc(user.uid).update({
        'fcm_token': token,
        'fcm_token_updated_at': FieldValue.serverTimestamp(),
      });
      debugPrint('FCM token saved for user ${user.uid}');
    } catch (e) {
      debugPrint('Failed to save FCM token: $e');
    }
  }

  /// Handle foreground messages (show in-app notification).
  void _handleForegroundMessage(RemoteMessage message) {
    debugPrint(
      'FCM foreground message: ${message.notification?.title} - ${message.notification?.body}',
    );
    // TODO (Phase 4): Show in-app snackbar/banner
  }

  /// Handle notification tap — navigate to campaign detail.
  void _handleNotificationTap(RemoteMessage message) {
    final campaignId = message.data['campaign_id'];
    if (campaignId != null) {
      debugPrint('Navigate to campaign: $campaignId');
      // Navigation will be handled by the app's router in Phase 4
    }
  }
}

final notificationService = NotificationService();
