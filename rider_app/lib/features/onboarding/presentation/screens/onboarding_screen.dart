import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/theme.dart';
import '../../../../core/constants/constants.dart';
import '../../../../core/router/app_router.dart';
import '../../../../core/providers/providers.dart';
import '../../../../shared/models/models.dart';

/// Welcome/Onboarding intro screen
class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final payoutLogAsync = ref.watch(publicPayoutLogProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Spacer(),

              // Illustration
              Container(
                    width: 280,
                    height: 280,
                    decoration: BoxDecoration(
                      gradient: AppColors.primaryGradient,
                      borderRadius: BorderRadius.circular(140),
                    ),
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        // Outer ring
                        Container(
                          width: 240,
                          height: 240,
                          decoration: BoxDecoration(
                            color: AppColors.white.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(120),
                          ),
                        ),
                        // Inner ring
                        Container(
                          width: 180,
                          height: 180,
                          decoration: BoxDecoration(
                            color: AppColors.white.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(90),
                          ),
                        ),
                        // Shield icon
                        const Icon(
                          Icons.shield_rounded,
                          size: 80,
                          color: AppColors.white,
                        ),
                      ],
                    ),
                  )
                  .animate()
                  .scale(duration: 500.ms, curve: Curves.elasticOut)
                  .fadeIn(duration: 400.ms),

              const SizedBox(height: 48),

              // Title
              Text(
                    AppStrings.welcomeTitle,
                    style: AppTypography.displayMedium,
                    textAlign: TextAlign.center,
                  )
                  .animate(delay: 200.ms)
                  .fadeIn(duration: 400.ms)
                  .slideY(begin: 0.2, end: 0),

              const SizedBox(height: 16),

              // Subtitle
              Text(
                AppStrings.welcomeSubtitle,
                style: AppTypography.bodyLarge.copyWith(
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ).animate(delay: 300.ms).fadeIn(duration: 400.ms),

              const SizedBox(height: 16),

              // Features list
              _buildFeatureItem(
                Icons.flash_on_rounded,
                'Instant payouts when disruptions hit',
                AppColors.warning,
              ).animate(delay: 400.ms).fadeIn().slideX(begin: -0.1),

              _buildFeatureItem(
                Icons.verified_rounded,
                'AI-powered automatic claim detection',
                AppColors.success,
              ).animate(delay: 500.ms).fadeIn().slideX(begin: -0.1),

              _buildFeatureItem(
                Icons.lock_rounded,
                'Blockchain-verified transparent records',
                AppColors.secondary,
              ).animate(delay: 600.ms).fadeIn().slideX(begin: -0.1),

              const SizedBox(height: 10),

              payoutLogAsync
                  .when(
                    data: (entries) => _PayoutLogPreview(entries: entries),
                    loading: () => const SizedBox.shrink(),
                    error: (_, _) => const SizedBox.shrink(),
                  )
                  .animate(delay: 650.ms)
                  .fadeIn(duration: 300.ms),

              const Spacer(),

              // Get Started Button
              SizedBox(
                    width: double.infinity,
                    height: 56,
                    child: ElevatedButton(
                      onPressed: () => context.go(AppRoutes.persona),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            AppStrings.getStarted,
                            style: AppTypography.buttonLarge.copyWith(
                              color: AppColors.white,
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Icon(
                            Icons.arrow_forward_rounded,
                            color: AppColors.white,
                          ),
                        ],
                      ),
                    ),
                  )
                  .animate(delay: 700.ms)
                  .fadeIn(duration: 400.ms)
                  .slideY(begin: 0.3, end: 0),

              const SizedBox(height: 16),

              OutlinedButton(
                onPressed: () {
                  ref.read(onboardingProvider.notifier).setPurchaseLater(true);
                  context.go(AppRoutes.home);
                },
                child: const Text('I will buy protection later'),
              ).animate(delay: 740.ms).fadeIn(duration: 300.ms),

              const SizedBox(height: 8),

              TextButton(
                onPressed: () => context.go(AppRoutes.login),
                child: Text(
                  'Already have an account? Sign in',
                  style: AppTypography.labelLarge.copyWith(
                    color: AppColors.primary,
                  ),
                ),
              ).animate(delay: 760.ms).fadeIn(duration: 300.ms),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFeatureItem(IconData icon, String text, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              text,
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PayoutLogPreview extends StatelessWidget {
  final List<PublicPayoutLogEntry> entries;

  const _PayoutLogPreview({required this.entries});

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return const SizedBox.shrink();
    }

    final top = entries.take(2).toList();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Public payout log', style: AppTypography.labelLarge),
          const SizedBox(height: 6),
          ...top.map(
            (entry) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                '${entry.rider} • ${entry.triggerType} • Rs ${entry.payoutAmount.toStringAsFixed(0)}',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
