import 'package:go_router/go_router.dart';

import '../../features/splash/presentation/screens/splash_screen.dart';
import '../../features/onboarding/presentation/screens/onboarding_screen.dart';
import '../../features/onboarding/presentation/screens/persona_screen.dart';
import '../../features/onboarding/presentation/screens/profile_screen.dart';
import '../../features/onboarding/presentation/screens/login_screen.dart';
import '../../features/onboarding/presentation/screens/zone_screen.dart';
import '../../features/onboarding/presentation/screens/review_screen.dart';
import '../../features/onboarding/presentation/screens/success_screen.dart';
import '../../features/home/presentation/screens/home_screen.dart';
import '../../features/home/presentation/screens/dashboard_screen.dart';
import '../../features/home/presentation/screens/delivery_history_screen.dart';
import '../../features/claims/presentation/screens/claims_screen.dart';
import '../../features/policy/presentation/screens/policy_screen.dart';
import '../../features/profile/presentation/screens/profile_settings_screen.dart';

/// App route paths
class AppRoutes {
  AppRoutes._();

  static const String splash = '/';
  static const String onboarding = '/onboarding';
  static const String login = '/login';
  static const String persona = '/onboarding/persona';
  static const String profile = '/onboarding/profile';
  static const String zone = '/onboarding/zone';
  static const String review = '/onboarding/review';
  static const String success = '/onboarding/success';
  static const String home = '/home';
  static const String deliveryHistory = '/delivery-history';
  static const String claims = '/claims';
  static const String policy = '/policy';
  static const String settings = '/settings';
}

/// App router configuration using GoRouter
final GoRouter appRouter = GoRouter(
  initialLocation: AppRoutes.splash,
  debugLogDiagnostics: true,
  routes: [
    // Splash
    GoRoute(
      path: AppRoutes.splash,
      name: 'splash',
      builder: (context, state) => const SplashScreen(),
    ),
    GoRoute(
      path: AppRoutes.deliveryHistory,
      name: 'delivery-history',
      builder: (context, state) => const DeliveryHistoryScreen(),
    ),

    // Onboarding Flow
    GoRoute(
      path: AppRoutes.onboarding,
      name: 'onboarding',
      builder: (context, state) => const OnboardingScreen(),
    ),
    GoRoute(
      path: AppRoutes.login,
      name: 'login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: AppRoutes.persona,
      name: 'persona',
      builder: (context, state) => const PersonaScreen(),
    ),
    GoRoute(
      path: AppRoutes.profile,
      name: 'profile',
      builder: (context, state) => const ProfileScreen(),
    ),
    GoRoute(
      path: AppRoutes.zone,
      name: 'zone',
      builder: (context, state) => const ZoneScreen(),
    ),
    GoRoute(
      path: AppRoutes.review,
      name: 'review',
      builder: (context, state) => const ReviewScreen(),
    ),
    GoRoute(
      path: AppRoutes.success,
      name: 'success',
      builder: (context, state) => const SuccessScreen(),
    ),

    // Main App (with bottom navigation)
    ShellRoute(
      builder: (context, state, child) => HomeScreen(child: child),
      routes: [
        GoRoute(
          path: AppRoutes.home,
          name: 'home',
          pageBuilder: (context, state) =>
              const NoTransitionPage(child: DashboardScreen()),
        ),
        GoRoute(
          path: AppRoutes.claims,
          name: 'claims',
          pageBuilder: (context, state) =>
              const NoTransitionPage(child: ClaimsScreen()),
        ),
        GoRoute(
          path: AppRoutes.policy,
          name: 'policy',
          pageBuilder: (context, state) =>
              const NoTransitionPage(child: PolicyScreen()),
        ),
        GoRoute(
          path: AppRoutes.settings,
          name: 'settings',
          pageBuilder: (context, state) =>
              const NoTransitionPage(child: ProfileSettingsScreen()),
        ),
      ],
    ),
  ],
);
