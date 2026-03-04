import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers/providers.dart';
import '../../../../core/theme/theme.dart';
import '../../../../core/router/app_router.dart';

/// Success screen after policy activation
class SuccessScreen extends ConsumerWidget {
  const SuccessScreen({super.key});

  String _generateTxHash() {
    const chars = '0123456789abcdef';
    return '0x${List.generate(64, (i) => chars[(i * 7) % 16]).join()}';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final riderAsync = ref.watch(currentRiderProvider);
    final policyAsync = ref.watch(activePolicyProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Spacer(),

              // Success animation
              Container(
                    width: 120,
                    height: 120,
                    decoration: BoxDecoration(
                      gradient: AppColors.shieldGradient,
                      borderRadius: BorderRadius.circular(60),
                      boxShadow: [
                        BoxShadow(
                          color: AppColors.success.withOpacity(0.3),
                          blurRadius: 30,
                          offset: const Offset(0, 10),
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.shield_rounded,
                      color: AppColors.white,
                      size: 56,
                    ),
                  )
                  .animate()
                  .scale(duration: 500.ms, curve: Curves.elasticOut)
                  .fadeIn(),

              const SizedBox(height: 32),

              Text(
                "You're Protected!",
                style: AppTypography.displayMedium.copyWith(
                  color: AppColors.success,
                ),
                textAlign: TextAlign.center,
              ).animate(delay: 200.ms).fadeIn().slideY(begin: 0.2),

              const SizedBox(height: 12),

              policyAsync
                  .when(
                    data: (policy) => riderAsync.when(
                      data: (rider) => Text(
                        'Policy active for ${rider?.name ?? 'your account'}.\nLive triggers are now monitoring ${policy?.zoneId ?? 'your zone'} 24/7.\nVerified payouts will move automatically when a disruption hits.',
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.textSecondary,
                          height: 1.6,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      loading: () => const SizedBox.shrink(),
                      error: (_, _) => const SizedBox.shrink(),
                    ),
                    loading: () => const SizedBox.shrink(),
                    error: (_, _) => const SizedBox.shrink(),
                  )
                  .animate(delay: 300.ms)
                  .fadeIn(),

              const SizedBox(height: 32),

              // Policy details grid
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.border),
                ),
                child: policyAsync.when(
                  data: (policy) => Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: _buildDetailItem(
                              'Zone',
                              policy?.zoneId ?? '-',
                            ),
                          ),
                          Expanded(
                            child: _buildDetailItem(
                              'Premium',
                              'Rs 99 + taxes / week',
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          Expanded(
                            child: _buildDetailItem(
                              'Coverage',
                              'Rs ${(policy?.coverage ?? 0).toStringAsFixed(0)}',
                            ),
                          ),
                          Expanded(
                            child: _buildDetailItem(
                              'Status',
                              (policy?.status ?? 'active').toUpperCase(),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                  loading: () => const SizedBox.shrink(),
                  error: (_, _) => const SizedBox.shrink(),
                ),
              ).animate(delay: 400.ms).fadeIn().slideY(begin: 0.1),

              const SizedBox(height: 24),

              // TX Hash
              Column(
                children: [
                  Text(
                    'Blockchain TX Hash:',
                    style: AppTypography.labelSmall.copyWith(
                      color: AppColors.textTertiary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.success.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: AppColors.success.withOpacity(0.2),
                      ),
                    ),
                    child: Text(
                      policyAsync.valueOrNull?.txHash ?? _generateTxHash(),
                      style: AppTypography.monoSmall.copyWith(
                        color: AppColors.success,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ).animate(delay: 500.ms).fadeIn(),

              const Spacer(),

              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () => context.go(AppRoutes.home),
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
                        'View My Dashboard',
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
              ).animate(delay: 600.ms).fadeIn().slideY(begin: 0.2),

              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailItem(String label, String value) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label.toUpperCase(),
            style: AppTypography.caption.copyWith(
              color: AppColors.textTertiary,
              letterSpacing: 1,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: AppTypography.titleMedium.copyWith(
              color: AppColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
