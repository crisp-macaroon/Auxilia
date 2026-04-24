import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../../core/providers/providers.dart';
import '../../../../core/router/app_router.dart';
import '../../../../core/services/api_service.dart';
import '../../../../core/services/notification_service.dart';
import '../../../../core/theme/theme.dart';
import '../../../../shared/models/models.dart';

// Provider for notification enabled state
final notificationsEnabledProvider = StateProvider<bool>((ref) => true);

// Provider for selected language
final selectedLanguageProvider = StateProvider<String>((ref) => 'en');

// Available languages
const Map<String, String> availableLanguages = {
  'en': 'English',
  'hi': 'हिंदी (Hindi)',
  'ta': 'தமிழ் (Tamil)',
  'te': 'తెలుగు (Telugu)',
  'kn': 'ಕನ್ನಡ (Kannada)',
  'ml': 'മലയാളം (Malayalam)',
  'mr': 'मराठी (Marathi)',
  'bn': 'বাংলা (Bengali)',
};

class ProfileSettingsScreen extends ConsumerStatefulWidget {
  const ProfileSettingsScreen({super.key});

  @override
  ConsumerState<ProfileSettingsScreen> createState() =>
      _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends ConsumerState<ProfileSettingsScreen> {
  final NotificationService _notificationService = NotificationService();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    await _notificationService.initialize();
    final prefs = await SharedPreferences.getInstance();

    // Load notification setting
    final notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
    ref.read(notificationsEnabledProvider.notifier).state =
        notificationsEnabled;

    // Load language setting
    final language = prefs.getString('selected_language') ?? 'en';
    ref.read(selectedLanguageProvider.notifier).state = language;
  }

  @override
  Widget build(BuildContext context) {
    final riderAsync = ref.watch(currentRiderProvider);
    final notificationsEnabled = ref.watch(notificationsEnabledProvider);
    final selectedLanguage = ref.watch(selectedLanguageProvider);

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
                        loyaltyPoints: rider.loyaltyPoints,
                      );
                    },
                    loading: () => const _LoadingCard(),
                    error: (_, __) => const _MessageCard(
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
                error: (_, __) => const SizedBox.shrink(),
              ),
              const SizedBox(height: 24),
              Text('Settings', style: AppTypography.titleLarge),
              const SizedBox(height: 16),

              // Notifications toggle
              _NotificationSettingItem(
                enabled: notificationsEnabled,
                onChanged: (value) async {
                  ref.read(notificationsEnabledProvider.notifier).state = value;
                  await _notificationService.setEnabled(value);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          value
                              ? 'Notifications enabled'
                              : 'Notifications disabled',
                        ),
                        duration: const Duration(seconds: 2),
                      ),
                    );
                  }
                },
              ).animate(delay: 200.ms).fadeIn().slideX(begin: 0.05),

              // Language selector
              _LanguageSettingItem(
                currentLanguage: selectedLanguage,
                onLanguageSelected: (langCode) async {
                  ref.read(selectedLanguageProvider.notifier).state = langCode;
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setString('selected_language', langCode);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          'Language changed to ${availableLanguages[langCode]}',
                        ),
                        duration: const Duration(seconds: 2),
                      ),
                    );
                  }
                },
              ).animate(delay: 260.ms).fadeIn().slideX(begin: 0.05),

              // Policy Updates (renamed from Coverage Feed)
              _buildTappableItem(
                Icons.shield_outlined,
                'Policy Updates',
                'View your policy history and changes',
                1,
                () => _showPolicyUpdates(context),
              ),

              // Help & Support
              _buildTappableItem(
                Icons.help_outline_rounded,
                'Help & Support',
                'FAQs and support contact',
                2,
                () => _showHelpSupport(context),
              ),

              const SizedBox(height: 24),

              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () async {
                    await ref.read(onboardingProvider.notifier).logout();
                    if (!context.mounted) return;
                    context.go(AppRoutes.login);
                  },
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text('Log Out'),
                ),
              ).animate(delay: 320.ms).fadeIn(),

              const SizedBox(height: 24),

              // TEST TRIGGER BUTTON - For demo purposes
              _TestTriggerCard(
                onTestNotification: () async {
                  await _notificationService.sendTestNotification();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Test notification sent!'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  }
                },
                onTestMovementAlert: () async {
                  await _notificationService.notifyMovementDetected();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Movement alert sent!'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  }
                },
                onTestTriggerAlert: () async {
                  await _notificationService.notifyTriggerDetected(
                    'Road Disruption',
                    'Heavy waterlogging reported in your zone',
                  );
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Trigger alert sent!'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  }
                },
                onTestClaimPaid: () async {
                  await _notificationService.notifyClaimUpdate(
                    'CLM-TEST-001',
                    'paid',
                  );
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Claim paid notification sent!'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  }
                },
                onTestPolicyExpired: () async {
                  await _notificationService.notifyPolicyExpired();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Policy expired notification sent!'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  }
                },
                onRunFullWorkflow: () async {
                  final rider = await ref.read(currentRiderProvider.future);
                  final policy = await ref.read(activePolicyProvider.future);
                  final api = ref.read(apiServiceProvider);

                  if (rider == null || policy == null) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Need active rider + policy first'),
                        ),
                      );
                    }
                    return;
                  }

                  const demoLat = 12.9756;
                  const demoLon = 77.6062;
                  const orderId = 'ORDER-DEMO-001';

                  final locationRes = await api.updateRiderLocation(
                    riderId: rider.id,
                    latitude: demoLat,
                    longitude: demoLon,
                  );

                  final checkInRes = await api.deliveryCheckIn(
                    riderId: rider.id,
                    orderId: orderId,
                    deliveryLat: demoLat,
                    deliveryLon: demoLon,
                    riderLat: demoLat,
                    riderLon: demoLon,
                  );

                  final triggerRes = await api.runTriggerCheck();
                  final zoneTriggers = await api.getZoneTriggers(policy.zoneId);

                  ApiResponse<Claim>? claimRes;
                  TriggerStatusModel? activeTrigger;
                  final triggers = zoneTriggers.data ?? <TriggerStatusModel>[];
                  for (final trigger in triggers) {
                    if (trigger.isActive) {
                      activeTrigger = trigger;
                      break;
                    }
                  }

                  if (activeTrigger != null) {
                    claimRes = await api.createClaim(
                      policyId: policy.id,
                      triggerType: activeTrigger.triggerType,
                    );
                  }

                  if (context.mounted) {
                    final msg = activeTrigger == null
                        ? 'Workflow done | Location: ${locationRes.success} | Check-in: ${checkInRes.success} | Trigger scan: ${triggerRes.success} | Claim skipped: no active trigger'
                        : 'Workflow done | Location: ${locationRes.success} | Check-in: ${checkInRes.success} | Trigger scan: ${triggerRes.success} | Claim: ${claimRes?.success ?? false} (${activeTrigger.triggerType})';
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(msg),
                        duration: const Duration(seconds: 4),
                      ),
                    );
                  }

                  ref.invalidate(currentRiderProvider);
                  ref.invalidate(triggersProvider);
                  ref.invalidate(claimsProvider);
                  ref.invalidate(claimsSummaryProvider);
                  ref.invalidate(latestPolicyProvider);
                },
              ).animate(delay: 400.ms).fadeIn(),

              const SizedBox(height: 24),

              // Logout button
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

  Widget _buildTappableItem(
    IconData icon,
    String title,
    String subtitle,
    int index,
    VoidCallback onTap,
  ) {
    return GestureDetector(
          onTap: onTap,
          child: Container(
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
                const Icon(
                  Icons.chevron_right_rounded,
                  color: AppColors.textTertiary,
                ),
              ],
            ),
          ),
        )
        .animate(delay: Duration(milliseconds: 320 + (index * 60)))
        .fadeIn()
        .slideX(begin: 0.05);
  }

  void _showPolicyUpdates(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => const _PolicyUpdatesSheet(),
    );
  }

  void _showHelpSupport(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => const _HelpSupportSheet(),
    );
  }
}

// Notification settings item with working toggle
class _NotificationSettingItem extends StatelessWidget {
  final bool enabled;
  final ValueChanged<bool> onChanged;

  const _NotificationSettingItem({
    required this.enabled,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
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
            child: const Icon(
              Icons.notifications_rounded,
              color: AppColors.textSecondary,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Notifications', style: AppTypography.titleSmall),
                const SizedBox(height: 2),
                Text(
                  enabled
                      ? 'Alerts for triggers, claims & safety'
                      : 'Notifications disabled',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textTertiary,
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: enabled,
            onChanged: onChanged,
            activeColor: AppColors.primary,
          ),
        ],
      ),
    );
  }
}

// Language settings item with selector
class _LanguageSettingItem extends StatelessWidget {
  final String currentLanguage;
  final ValueChanged<String> onLanguageSelected;

  const _LanguageSettingItem({
    required this.currentLanguage,
    required this.onLanguageSelected,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => _showLanguageSelector(context),
      child: Container(
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
              child: const Icon(
                Icons.language_rounded,
                color: AppColors.textSecondary,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Language', style: AppTypography.titleSmall),
                  const SizedBox(height: 2),
                  Text(
                    availableLanguages[currentLanguage] ?? 'English',
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.textTertiary,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.chevron_right_rounded,
              color: AppColors.textTertiary,
            ),
          ],
        ),
      ),
    );
  }

  void _showLanguageSelector(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => _LanguageSelectorSheet(
        currentLanguage: currentLanguage,
        onLanguageSelected: (lang) {
          onLanguageSelected(lang);
          Navigator.pop(context);
        },
      ),
    );
  }
}

class _LanguageSelectorSheet extends StatelessWidget {
  final String currentLanguage;
  final ValueChanged<String> onLanguageSelected;

  const _LanguageSelectorSheet({
    required this.currentLanguage,
    required this.onLanguageSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Select Language', style: AppTypography.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Choose your preferred language',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 20),
          ...availableLanguages.entries.map((entry) {
            final isSelected = entry.key == currentLanguage;
            return ListTile(
              onTap: () => onLanguageSelected(entry.key),
              leading: Icon(
                isSelected
                    ? Icons.radio_button_checked
                    : Icons.radio_button_off,
                color: isSelected ? AppColors.primary : AppColors.textTertiary,
              ),
              title: Text(
                entry.value,
                style: AppTypography.bodyMedium.copyWith(
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
              trailing: isSelected
                  ? const Icon(Icons.check, color: AppColors.primary)
                  : null,
            );
          }),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}

// Test Trigger Card for demo purposes
class _TestTriggerCard extends StatelessWidget {
  final VoidCallback onTestNotification;
  final VoidCallback onTestMovementAlert;
  final VoidCallback onTestTriggerAlert;
  final VoidCallback onTestClaimPaid;
  final VoidCallback onTestPolicyExpired;
  final VoidCallback onRunFullWorkflow;

  const _TestTriggerCard({
    required this.onTestNotification,
    required this.onTestMovementAlert,
    required this.onTestTriggerAlert,
    required this.onTestClaimPaid,
    required this.onTestPolicyExpired,
    required this.onRunFullWorkflow,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.warning.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.warning.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.science_rounded, color: AppColors.warning, size: 24),
              const SizedBox(width: 12),
              Text(
                'Test Triggers (Demo)',
                style: AppTypography.titleMedium.copyWith(
                  color: AppColors.warning,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Test notifications to verify the app is working correctly.',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _TestButton(
                label: 'Test Alert',
                icon: Icons.notifications_active,
                onTap: onTestNotification,
              ),
              _TestButton(
                label: 'Movement',
                icon: Icons.directions_bike,
                onTap: onTestMovementAlert,
              ),
              _TestButton(
                label: 'Trigger',
                icon: Icons.warning_amber_rounded,
                onTap: onTestTriggerAlert,
              ),
              _TestButton(
                label: 'Claim Paid',
                icon: Icons.paid_rounded,
                onTap: onTestClaimPaid,
              ),
              _TestButton(
                label: 'Policy Expired',
                icon: Icons.event_busy_rounded,
                onTap: onTestPolicyExpired,
              ),
              _TestButton(
                label: 'Full Workflow',
                icon: Icons.play_circle_fill_rounded,
                onTap: onRunFullWorkflow,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TestButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  const _TestButton({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 16, color: AppColors.primary),
              const SizedBox(width: 6),
              Text(
                label,
                style: AppTypography.labelSmall.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// Policy Updates Sheet
class _PolicyUpdatesSheet extends StatelessWidget {
  const _PolicyUpdatesSheet();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.7,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.shield_outlined, color: AppColors.primary),
              const SizedBox(width: 12),
              Text('Policy Updates', style: AppTypography.titleLarge),
            ],
          ),
          const SizedBox(height: 20),
          Expanded(
            child: ListView(
              children: const [
                _PolicyUpdateItem(
                  title: 'Weekly Premium Model',
                  description: 'Pay Rs 99/week for Q-Commerce coverage',
                  icon: Icons.payments_rounded,
                  isNew: true,
                ),
                _PolicyUpdateItem(
                  title: 'Loss of Income Protection',
                  description:
                      'Coverage for road disruptions, weather events, and traffic surges that affect your earnings',
                  icon: Icons.umbrella_rounded,
                ),
                _PolicyUpdateItem(
                  title: 'Instant Claims',
                  description:
                      'AI-powered claims processing with automatic payout within 24 hours',
                  icon: Icons.flash_on_rounded,
                ),
                _PolicyUpdateItem(
                  title: 'Zone-Based Coverage',
                  description:
                      'Coverage amount adjusted based on your operating zone risk profile',
                  icon: Icons.map_rounded,
                ),
                _PolicyUpdateItem(
                  title: 'Blockchain Verification',
                  description:
                      'All policy terms and claims are recorded on-chain for transparency',
                  icon: Icons.verified_rounded,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PolicyUpdateItem extends StatelessWidget {
  final String title;
  final String description;
  final IconData icon;
  final bool isNew;

  const _PolicyUpdateItem({
    required this.title,
    required this.description,
    required this.icon,
    this.isNew = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: AppColors.primary, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(title, style: AppTypography.titleSmall),
                    ),
                    if (isNew)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.success,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          'NEW',
                          style: AppTypography.caption.copyWith(
                            color: AppColors.white,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textSecondary,
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

// Help & Support Sheet
class _HelpSupportSheet extends StatelessWidget {
  const _HelpSupportSheet();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.8,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.help_outline_rounded, color: AppColors.primary),
              const SizedBox(width: 12),
              Text('Help & Support', style: AppTypography.titleLarge),
            ],
          ),
          const SizedBox(height: 20),
          Expanded(
            child: ListView(
              children: const [
                _FAQItem(
                  question: 'How does Auxilia work?',
                  answer:
                      'Auxilia uses AI to monitor real-time conditions like weather, traffic, and road disruptions in your zone. When these events affect your ability to earn, we automatically process a claim and pay you for lost income.',
                ),
                _FAQItem(
                  question: 'What triggers a claim?',
                  answer:
                      'Claims are triggered by: Heavy rain or flooding, severe traffic congestion, road closures, and other verified delivery disruptions that impact gig worker earnings.',
                ),
                _FAQItem(
                  question: 'How much coverage do I get?',
                  answer:
                      'Q-Commerce riders get up to Rs 2000/week coverage. The exact payout depends on the severity of the trigger and your policy terms.',
                ),
                _FAQItem(
                  question: 'How fast are payouts?',
                  answer:
                      'Most claims are processed automatically within minutes. Payouts are typically credited within 24 hours of claim approval.',
                ),
                _FAQItem(
                  question: 'How do I file a claim?',
                  answer:
                      'Claims are often filed automatically when triggers are detected. You can also manually file a claim from the Claims tab by tapping "File New Claim" and entering the delivery details.',
                ),
                _FAQItem(
                  question: 'What if my claim is rejected?',
                  answer:
                      'If your claim is rejected, you\'ll receive a notification with the reason. Common reasons include: trigger not verified, delivery outside policy hours, or duplicate claim.',
                ),
                Divider(height: 32),
                _ContactCard(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _FAQItem extends StatefulWidget {
  final String question;
  final String answer;

  const _FAQItem({required this.question, required this.answer});

  @override
  State<_FAQItem> createState() => _FAQItemState();
}

class _FAQItemState extends State<_FAQItem> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () => setState(() => _expanded = !_expanded),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      widget.question,
                      style: AppTypography.titleSmall,
                    ),
                  ),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    color: AppColors.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Text(
                widget.answer,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ContactCard extends StatelessWidget {
  const _ContactCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Need more help?', style: AppTypography.titleMedium),
          const SizedBox(height: 8),
          Text(
            'Contact our support team',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _ContactButton(
                  icon: Icons.email_rounded,
                  label: 'Email',
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('support@auxilia.sabarixr.me'),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _ContactButton(
                  icon: Icons.chat_rounded,
                  label: 'Chat',
                  onTap: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Chat coming soon!')),
                    );
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ContactButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _ContactButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 18, color: AppColors.primary),
              const SizedBox(width: 8),
              Text(label, style: AppTypography.buttonSmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProfileCard extends StatelessWidget {
  final String name;
  final String phone;
  final String persona;
  final int loyaltyPoints;

  const _ProfileCard({
    required this.name,
    required this.phone,
    required this.persona,
    required this.loyaltyPoints,
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
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(
                      Icons.stars_rounded,
                      size: 16,
                      color: AppColors.warning,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '$loyaltyPoints tokens',
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
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
