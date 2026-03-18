import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/providers/providers.dart';
import '../../../../core/theme/theme.dart';
import '../../../../shared/models/models.dart';

class PolicyScreen extends ConsumerWidget {
  const PolicyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final policyAsync = ref.watch(activePolicyProvider);
    final weatherAsync = ref.watch(weatherProvider);
    final triggersAsync = ref.watch(triggersProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Active Policy', style: AppTypography.displaySmall),
              const SizedBox(height: 8),
              Text(
                'Your live coverage details and trigger monitor.',
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 24),
              policyAsync.when(
                data: (policy) {
                  if (policy == null) {
                    return const _EmptyPolicyCard();
                  }
                  return _PolicyHero(policy: policy);
                },
                loading: () => const _LoadingBlock(height: 240),
                error: (_, _) => const _EmptyPolicyCard(),
              ),
              const SizedBox(height: 24),
              policyAsync
                  .when(
                    data: (policy) {
                      if (policy == null) {
                        return const SizedBox.shrink();
                      }
                      return Container(
                        padding: const EdgeInsets.all(20),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Column(
                          children: [
                            _buildDetailRow('Zone', policy.zoneId),
                            _buildDivider(),
                            _buildDetailRow(
                              'Premium',
                              'Rs ${policy.premium.toStringAsFixed(0)} / month',
                            ),
                            _buildDivider(),
                            _buildDetailRow(
                              'Coverage',
                              'Rs ${policy.coverage.toStringAsFixed(0)}',
                            ),
                            _buildDivider(),
                            _buildDetailRow(
                              'Renews',
                              DateFormat(
                                'EEE, MMM d, yyyy',
                              ).format(policy.endDate),
                            ),
                            _buildDivider(),
                            _buildDetailRow(
                              'Policy Hash',
                              policy.txHash ?? 'Pending',
                              isMono: true,
                            ),
                          ],
                        ),
                      );
                    },
                    loading: () => const _LoadingBlock(height: 210),
                    error: (_, _) => const SizedBox.shrink(),
                  )
                  .animate(delay: 200.ms)
                  .fadeIn()
                  .slideY(begin: 0.1),
              const SizedBox(height: 24),
              Text('Live Trigger Monitor', style: AppTypography.titleLarge),
              const SizedBox(height: 4),
              weatherAsync.when(
                data: (weather) => Text(
                  weather == null
                      ? 'Waiting for weather feed'
                      : 'Weather ${weather.condition} · ${weather.temperature.toStringAsFixed(0)} C',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.success,
                  ),
                ),
                loading: () => Text(
                  'Loading live signals...',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                error: (_, _) => Text(
                  'Live signals unavailable',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.warning,
                  ),
                ),
              ),
              const SizedBox(height: 16),
              triggersAsync.when(
                data: (triggers) {
                  if (triggers.isEmpty) {
                    return const _EmptyPolicyCard(
                      title: 'No trigger data yet',
                      subtitle:
                          'Run backend trigger checks to populate this monitor.',
                    );
                  }
                  return Column(
                    children: triggers
                        .asMap()
                        .entries
                        .map(
                          (entry) => _TriggerItem(
                            trigger: entry.value,
                            index: entry.key,
                          ),
                        )
                        .toList(),
                  );
                },
                loading: () => const _LoadingBlock(height: 220),
                error: (_, _) => const _EmptyPolicyCard(
                  title: 'Trigger feed unavailable',
                  subtitle: 'Backend data will appear here once the API is up.',
                ),
              ),
              const SizedBox(height: 100),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value, {bool isMono = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              overflow: TextOverflow.ellipsis,
              style: isMono
                  ? AppTypography.monoSmall.copyWith(color: AppColors.success)
                  : AppTypography.titleSmall,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDivider() => Divider(color: AppColors.border, height: 1);
}

class _PolicyHero extends StatelessWidget {
  final Policy policy;

  const _PolicyHero({required this.policy});

  @override
  Widget build(BuildContext context) {
    final progress = (policy.daysRemaining.clamp(0, 30) / 30);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: AppColors.primaryGradient,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          SizedBox(
            width: 120,
            height: 120,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CircularProgressIndicator(
                  value: progress,
                  strokeWidth: 8,
                  backgroundColor: AppColors.white.withOpacity(0.2),
                  valueColor: const AlwaysStoppedAnimation(AppColors.white),
                ),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      '${policy.daysRemaining}',
                      style: AppTypography.displayLarge.copyWith(
                        color: AppColors.white,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      'days left',
                      style: AppTypography.labelSmall.copyWith(
                        color: AppColors.white.withOpacity(0.8),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              policy.isActive ? 'SHIELD ACTIVE' : 'EXPIRED',
              style: AppTypography.labelSmall.copyWith(
                color: AppColors.white,
                fontWeight: FontWeight.w700,
                letterSpacing: 1,
              ),
            ),
          ),
        ],
      ),
    ).animate().fadeIn().scale(begin: const Offset(0.95, 0.95));
  }
}

class _TriggerItem extends StatelessWidget {
  final TriggerStatusModel trigger;
  final int index;

  const _TriggerItem({required this.trigger, required this.index});

  @override
  Widget build(BuildContext context) {
    final statusColor = trigger.isActive
        ? AppColors.warning
        : AppColors.success;

    return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.border),
          ),
          child: Row(
            children: [
              Icon(
                Icons.sensors_rounded,
                color: AppColors.textSecondary,
                size: 24,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      trigger.triggerType.toUpperCase(),
                      style: AppTypography.titleSmall,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Current ${trigger.currentValue.toStringAsFixed(1)} | Threshold ${trigger.threshold.toStringAsFixed(1)}',
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  trigger.statusLabel,
                  style: AppTypography.labelSmall.copyWith(
                    color: statusColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        )
        .animate(delay: Duration(milliseconds: 300 + (index * 80)))
        .fadeIn()
        .slideX(begin: 0.05);
  }
}

class _EmptyPolicyCard extends StatelessWidget {
  final String title;
  final String subtitle;

  const _EmptyPolicyCard({
    this.title = 'No active policy found',
    this.subtitle =
        'Complete onboarding and create a policy to see live protection data.',
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTypography.titleMedium),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _LoadingBlock extends StatelessWidget {
  final double height;

  const _LoadingBlock({required this.height});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
      ),
    );
  }
}
