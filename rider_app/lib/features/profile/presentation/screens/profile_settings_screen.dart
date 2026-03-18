import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../../core/providers/providers.dart';
import '../../../../core/theme/theme.dart';

class ProfileSettingsScreen extends ConsumerWidget {
  const ProfileSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final riderAsync = ref.watch(currentRiderProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Profile', style: AppTypography.displaySmall),
              const SizedBox(height: 24),
              riderAsync
                  .when(
                    data: (rider) {
                      if (rider == null) {
                        return const _MessageCard(
                          title: 'No rider session',
                          subtitle:
                              'Register through onboarding to unlock profile data.',
                        );
                      }

                      return _ProfileCard(
                        name: rider.name,
                        phone: rider.phone,
                        persona: rider.persona,
                      );
                    },
                    loading: () => const _LoadingCard(),
                    error: (_, _) => const _MessageCard(
                      title: 'Unable to load profile',
                      subtitle: 'Check the backend connection and try again.',
                    ),
                  )
                  .animate()
                  .fadeIn(),
              const SizedBox(height: 24),
              riderAsync.when(
                data: (rider) => _RiskCard(riskScore: rider?.riskScore ?? 0),
                loading: () => const _LoadingCard(height: 170),
                error: (_, _) => const SizedBox.shrink(),
              ),
              const SizedBox(height: 24),
              Text('Settings', style: AppTypography.titleLarge),
              const SizedBox(height: 16),
              _buildSettingsItem(
                Icons.notifications_rounded,
                'Notifications',
                'Push alerts for triggers and payouts',
                true,
                0,
              ),
              _buildSettingsItem(
                Icons.language_rounded,
                'Language',
                'English',
                false,
                1,
              ),
              _buildSettingsItem(
                Icons.shield_outlined,
                'Coverage feed',
                'Live backend powered policy updates',
                false,
                2,
              ),
              _buildSettingsItem(
                Icons.help_outline_rounded,
                'Help & Support',
                'FAQs and support contact',
                false,
                3,
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: OutlinedButton(
                  onPressed: () async {
                    final prefs = await SharedPreferences.getInstance();
                    await prefs.remove('rider_id');
                    ref.invalidate(currentRiderIdProvider);
                    ref.invalidate(currentRiderProvider);
                    ref.invalidate(activePolicyProvider);
                    ref.invalidate(claimsProvider);
                    ref.invalidate(claimsSummaryProvider);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Logged out locally')),
                      );
                    }
                  },
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(color: AppColors.danger.withOpacity(0.5)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Text(
                    'Logout',
                    style: AppTypography.buttonMedium.copyWith(
                      color: AppColors.danger,
                    ),
                  ),
                ),
              ).animate(delay: 500.ms).fadeIn(),
              const SizedBox(height: 100),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSettingsItem(
    IconData icon,
    String title,
    String subtitle,
    bool hasSwitch,
    int index,
  ) {
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
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: AppColors.textSecondary, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppTypography.titleSmall),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
              if (hasSwitch)
                Switch(
                  value: true,
                  onChanged: (_) {},
                  activeColor: AppColors.primary,
                )
              else
                const Icon(
                  Icons.chevron_right_rounded,
                  color: AppColors.textTertiary,
                ),
            ],
          ),
        )
        .animate(delay: Duration(milliseconds: 200 + (index * 60)))
        .fadeIn()
        .slideX(begin: 0.05);
  }
}

class _ProfileCard extends StatelessWidget {
  final String name;
  final String phone;
  final String persona;

  const _ProfileCard({
    required this.name,
    required this.phone,
    required this.persona,
  });

  @override
  Widget build(BuildContext context) {
    final initials = name
        .split(' ')
        .where((part) => part.isNotEmpty)
        .take(2)
        .map((part) => part[0])
        .join();

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Center(
              child: Text(
                initials,
                style: AppTypography.headlineMedium.copyWith(
                  color: AppColors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: AppTypography.titleLarge),
                const SizedBox(height: 4),
                Text(
                  phone,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    persona.toUpperCase(),
                    style: AppTypography.caption.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RiskCard extends StatelessWidget {
  final double riskScore;

  const _RiskCard({required this.riskScore});

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
          Text('Zone Risk Profile', style: AppTypography.titleLarge),
          const SizedBox(height: 16),
          _RiskBar(
            label: 'Overall Risk',
            value: riskScore,
            color: AppColors.warning,
          ),
          const SizedBox(height: 16),
          _RiskBar(
            label: 'Payout Confidence',
            value: (1 - riskScore).clamp(0, 1),
            color: AppColors.success,
          ),
        ],
      ),
    );
  }
}

class _RiskBar extends StatelessWidget {
  final String label;
  final double value;
  final Color color;

  const _RiskBar({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            Text(
              value.toStringAsFixed(2),
              style: AppTypography.labelMedium.copyWith(
                color: color,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: value,
            minHeight: 8,
            backgroundColor: AppColors.border,
            valueColor: AlwaysStoppedAnimation(color),
          ),
        ),
      ],
    );
  }
}

class _MessageCard extends StatelessWidget {
  final String title;
  final String subtitle;

  const _MessageCard({required this.title, required this.subtitle});

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

class _LoadingCard extends StatelessWidget {
  final double height;

  const _LoadingCard({this.height = 120});

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
