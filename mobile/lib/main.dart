/// WardWatch - Main Entry Point
/// Initializes Firebase, App Check, and runs the app.
library;

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:firebase_auth/firebase_auth.dart';

import 'screens/onboarding_screen.dart';
import 'screens/auth_screen.dart';
import 'screens/discovery_map_screen.dart';
import 'services/notification_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase
  await Firebase.initializeApp();

  // Initialize Firebase App Check
  // - Android: PlayIntegrity in production, DebugProvider in debug mode
  // - iOS: DeviceCheck in production, DebugProvider in debug mode
  await FirebaseAppCheck.instance.activate(
    androidProvider: kDebugMode
        ? AndroidProvider.debug
        : AndroidProvider.playIntegrity,
    appleProvider: kDebugMode
        ? AppleProvider.debug
        : AppleProvider.deviceCheck,
  );

  // Initialize FCM notifications
  await notificationService.initialize();

  runApp(const WardWatchApp());
}

class WardWatchApp extends StatelessWidget {
  const WardWatchApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WardWatch',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1565C0),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        fontFamily: 'Roboto',
      ),
      home: const _AppRoot(),
    );
  }
}

/// Root widget that determines the initial screen based on auth state.
class _AppRoot extends StatelessWidget {
  const _AppRoot();

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: FirebaseAuth.instance.authStateChanges(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }

        final user = snapshot.data;

        if (user == null) {
          // Not logged in: show onboarding
          return const OnboardingScreen();
        }

        // Check if phone is verified via custom claims
        return FutureBuilder<IdTokenResult>(
          future: user.getIdTokenResult(true),
          builder: (context, tokenSnapshot) {
            if (tokenSnapshot.connectionState == ConnectionState.waiting) {
              return const Scaffold(
                body: Center(child: CircularProgressIndicator()),
              );
            }
            final claims = tokenSnapshot.data?.claims ?? {};
            final phoneVerified = claims['phone_verified'] == true;

            if (!phoneVerified) {
              return const AuthScreen();
            }

            return const DiscoveryMapScreen();
          },
        );
      },
    );
  }
}
