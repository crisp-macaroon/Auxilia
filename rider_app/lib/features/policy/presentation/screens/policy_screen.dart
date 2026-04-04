import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';

import '../../../../core/providers/providers.dart';
import '../../../../core/theme/theme.dart';
import '../../../../shared/models/models.dart';

class PolicyScreen extends ConsumerWidget {
  const PolicyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final policyAsync = ref.watch(activePolicyProvider);
    final latestPolicyAsync = ref.watch(latestPolicyProvider);
    final riderAsync = ref.watch(currentRiderProvider);
    final weatherAsync = ref.watch(weatherProvider);
    final triggersAsync = ref.watch(triggersProvider);
    final newsAsync = ref.watch(zoneNewsProvider);
    final trafficAsync = ref.watch(zoneTrafficProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(activePolicyProvider);
            ref.invalidate(latestPolicyProvider);
            ref.invalidate(weatherProvider);
            ref.invalidate(triggersProvider);
            ref.invalidate(zoneNewsProvider);
            ref.invalidate(zoneTrafficProvider);
          },
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Active Policy', style: AppTypography.displaySmall),
                const SizedBox(height: 8),
                Text(
                  'Your live coverage details and zone insights.',
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 24),
                policyAsync.when(
                  data: (policy) {
                    if (policy == null) {
                      final latestPolicy = latestPolicyAsync.valueOrNull;
                      final rider = riderAsync.valueOrNull;
                      if (latestPolicy != null) {
                        return _PolicyHero(policy: latestPolicy);
                      }
                      return _EmptyPolicyCard(
                        subtitle: rider == null
                            ? 'Complete onboarding and create a policy to see live protection data.'
                            : 'You are already onboarded. Buy your first policy to start protection.',
                      );
                    }
                    return _PolicyHero(policy: policy);
                  },
                  loading: () => const _LoadingBlock(height: 240),
                  error: (_, _) => const _EmptyPolicyCard(),
                ),
                const SizedBox(height: 16),
                // Policy Actions
                policyAsync.when(
                  data: (policy) {
                    final effectivePolicy = policy ?? latestPolicyAsync.valueOrNull;
                    if (effectivePolicy == null) return const SizedBox.shrink();
                    return _PolicyActions(policy: effectivePolicy);
                  },
                  loading: () => const SizedBox.shrink(),
                  error: (_, _) => const SizedBox.shrink(),
                ),
                const SizedBox(height: 24),
                // Policy Details Card
                policyAsync
                    .when(
                      data: (policy) {
                        final effectivePolicy = policy ?? latestPolicyAsync.valueOrNull;
                        if (effectivePolicy == null) {
                          return const SizedBox.shrink();
                        }
                        return _PolicyDetailsCard(policy: effectivePolicy);
                      },
                      loading: () => const _LoadingBlock(height: 210),
                      error: (_, _) => const SizedBox.shrink(),
                    )
                    .animate(delay: 200.ms)
                    .fadeIn()
                    .slideY(begin: 0.1),
                const SizedBox(height: 24),
                // Weather & Conditions Card
                _WeatherInsightsCard(
                  weatherAsync: weatherAsync,
                  trafficAsync: trafficAsync,
                ),
                const SizedBox(height: 24),
                // News & Alerts Card
                newsAsync.when(
                  data: (news) => _NewsAlertsCard(news: news),
                  loading: () => const _LoadingBlock(height: 150),
                  error: (_, _) => const SizedBox.shrink(),
                ),
                const SizedBox(height: 24),
                Text('Live Trigger Monitor', style: AppTypography.titleLarge),
                const SizedBox(height: 4),
                weatherAsync.when(
                  data: (weather) => Text(
                    weather == null
                        ? 'Waiting for weather feed'
                        : 'Weather ${weather.condition} · ${weather.temperature.toStringAsFixed(0)}°C',
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
                    subtitle:
                        'Backend data will appear here once the API is up.',
                  ),
                ),
                const SizedBox(height: 100),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PolicyDetailsCard extends StatelessWidget {
  final Policy policy;

  const _PolicyDetailsCard({required this.policy});

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
        children: [
          _buildDetailRow('Zone', policy.zoneId),
          _buildDivider(),
          _buildDetailRow(
            'Premium',
            'Rs ${policy.premium.toStringAsFixed(0)} / week',
          ),
          _buildDivider(),
          _buildDetailRow(
            'Coverage',
            'Rs ${policy.coverage.toStringAsFixed(0)}',
          ),
          _buildDivider(),
          _buildDetailRow(
            'Renews',
            DateFormat('EEE, MMM d, yyyy').format(policy.endDate),
          ),
          _buildDivider(),
          _buildDetailRow(
            'Policy Hash',
            policy.txHash ?? 'Awaiting blockchain confirmation...',
            isMono: true,
            isHash: policy.txHash != null,
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(
    String label,
    String value, {
    bool isMono = false,
    bool isHash = false,
  }) {
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
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (isHash)
                  Container(
                    margin: const EdgeInsets.only(right: 6),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.success.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Icon(
                      Icons.check,
                      size: 12,
                      color: AppColors.success,
                    ),
                  ),
                Flexible(
                  child: Text(
                    isMono && value.length > 16
                        ? '${value.substring(0, 8)}...${value.substring(value.length - 6)}'
                        : value,
                    textAlign: TextAlign.right,
                    overflow: TextOverflow.ellipsis,
                    style: isMono
                        ? AppTypography.monoSmall.copyWith(
                            color: isHash
                                ? AppColors.success
                                : AppColors.warning,
                          )
                        : AppTypography.titleSmall,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDivider() => Divider(color: AppColors.border, height: 1);
}

class _PolicyActions extends ConsumerStatefulWidget {
  final Policy policy;

  const _PolicyActions({required this.policy});

  @override
  ConsumerState<_PolicyActions> createState() => _PolicyActionsState();
}

class _PolicyActionsState extends ConsumerState<_PolicyActions> {
  bool _loading = false;
  late final Razorpay _razorpay;
  int? _pendingWeeks;
  Map<String, dynamic>? _pendingOrder;

  @override
  void initState() {
    super.initState();
    _razorpay = Razorpay();
    _razorpay.on(Razorpay.EVENT_PAYMENT_SUCCESS, _handlePaymentSuccess);
    _razorpay.on(Razorpay.EVENT_PAYMENT_ERROR, _handlePaymentError);
    _razorpay.on(Razorpay.EVENT_EXTERNAL_WALLET, _handleExternalWallet);
  }

  @override
  void dispose() {
    _razorpay.clear();
    super.dispose();
  }

  Future<void> _renewPolicy(int weeks) async {
    setState(() => _loading = true);

    final api = ref.read(apiServiceProvider);
    _pendingWeeks = weeks;

    final orderResponse = await api.createPolicyPaymentOrder(
      flowType: 'renew_policy',
      existingPolicyId: widget.policy.id,
      durationDays: weeks * 7,
    );

    if (!mounted) return;

    if (!orderResponse.success || orderResponse.data == null) {
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(orderResponse.error ?? 'Failed to start renewal payment'),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }

    _pendingOrder = orderResponse.data;

    if ((orderResponse.data!['checkout_mode'] ?? 'sandbox') == 'sandbox') {
      await _confirmRenewal(
        orderId: orderResponse.data!['order_id'] as String,
        paymentId: 'sandbox_payment_${DateTime.now().millisecondsSinceEpoch}',
        signature: 'sandbox_signature',
      );
      return;
    }

    _razorpay.open({
      'key': orderResponse.data!['key_id'],
      'amount': orderResponse.data!['amount'],
      'name': 'Auxilia',
      'description': 'Policy renewal',
      'order_id': orderResponse.data!['order_id'],
      'prefill': orderResponse.data!['prefill'] ?? {},
      'theme': {'color': '#F97316'},
    });
  }

  Future<void> _confirmRenewal({
    required String orderId,
    required String paymentId,
    String? signature,
  }) async {
    final api = ref.read(apiServiceProvider);
    final weeks = _pendingWeeks;
    if (_pendingOrder == null || weeks == null) {
      if (mounted) {
        setState(() => _loading = false);
      }
      return;
    }

    final response = await api.confirmPolicyPayment(
      flowType: 'renew_policy',
      orderId: orderId,
      paymentId: paymentId,
      signature: signature,
      existingPolicyId: widget.policy.id,
      durationDays: weeks * 7,
    );

    if (!mounted) return;

    setState(() => _loading = false);

    if (response.success) {
      ref.invalidate(activePolicyProvider);
      ref.invalidate(latestPolicyProvider);
      ref.invalidate(claimsProvider);
      ref.invalidate(claimsSummaryProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Policy renewed for $weeks week${weeks > 1 ? 's' : ''}!',
            ),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(response.error ?? 'Failed to renew policy'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    }
  }

  void _handlePaymentSuccess(PaymentSuccessResponse response) {
    final fallbackOrderId = _pendingOrder?['order_id'] as String?;
    final orderId = response.orderId ?? fallbackOrderId;
    if (orderId == null) {
      if (mounted) {
        setState(() => _loading = false);
      }
      return;
    }

    _confirmRenewal(
      orderId: orderId,
      paymentId: response.paymentId ?? '',
      signature: response.signature,
    );
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    if (!mounted) return;
    setState(() => _loading = false);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(response.message ?? 'Renewal payment cancelled'),
        backgroundColor: AppColors.danger,
      ),
    );
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    if (!mounted) return;
    setState(() => _loading = false);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('${response.walletName ?? 'External wallet'} is not supported'),
        backgroundColor: AppColors.warning,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final daysLeft = widget.policy.daysRemaining;
    final showRenew =
        daysLeft <= 3; // Show renew option when 3 or fewer days left
    final renewMessage = widget.policy.isActive
        ? 'Your policy expires in $daysLeft day${daysLeft != 1 ? 's' : ''}. Renew now to stay protected.'
        : 'Your last policy has expired. Renew now to restore protection.';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                showRenew ? Icons.update_rounded : Icons.shield_rounded,
                color: showRenew ? AppColors.warning : AppColors.success,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                showRenew ? 'Renew Your Coverage' : 'Manage Policy',
                style: AppTypography.titleSmall,
              ),
            ],
          ),
          if (showRenew) ...[
            const SizedBox(height: 8),
            Text(
              renewMessage,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _ActionButton(
                  label: '1 Week',
                  subtitle: 'Rs ${widget.policy.premium.toStringAsFixed(0)}',
                  onTap: _loading ? null : () => _renewPolicy(1),
                  isPrimary: true,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _ActionButton(
                  label: '2 Weeks',
                  subtitle:
                      'Rs ${(widget.policy.premium * 1.9).toStringAsFixed(0)}',
                  onTap: _loading ? null : () => _renewPolicy(2),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _ActionButton(
                  label: '4 Weeks',
                  subtitle:
                      'Rs ${(widget.policy.premium * 3.6).toStringAsFixed(0)}',
                  onTap: _loading ? null : () => _renewPolicy(4),
                ),
              ),
            ],
          ),
          if (_loading)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final String subtitle;
  final VoidCallback? onTap;
  final bool isPrimary;

  const _ActionButton({
    required this.label,
    required this.subtitle,
    this.onTap,
    this.isPrimary = false,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: BoxDecoration(
          color: isPrimary ? AppColors.primary : AppColors.background,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isPrimary ? AppColors.primary : AppColors.border,
          ),
        ),
        child: Column(
          children: [
            Text(
              label,
              style: AppTypography.labelMedium.copyWith(
                color: isPrimary ? AppColors.white : AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: AppTypography.labelSmall.copyWith(
                color: isPrimary
                    ? AppColors.white.withOpacity(0.8)
                    : AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WeatherInsightsCard extends StatelessWidget {
  final AsyncValue<WeatherData?> weatherAsync;
  final AsyncValue<Map<String, dynamic>> trafficAsync;

  const _WeatherInsightsCard({
    required this.weatherAsync,
    required this.trafficAsync,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.wb_sunny_rounded,
                  color: AppColors.warning,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Text('Weather & Conditions', style: AppTypography.titleSmall),
            ],
          ),
          const SizedBox(height: 16),
          weatherAsync.when(
            data: (weather) {
              if (weather == null) {
                return Text(
                  'Weather data unavailable',
                  style: AppTypography.bodySmall,
                );
              }
              return Column(
                children: [
                  Row(
                    children: [
                      _WeatherChip(
                        icon: Icons.thermostat_rounded,
                        label: '${weather.temperature.toStringAsFixed(0)}°C',
                        color: weather.temperature > 35
                            ? AppColors.danger
                            : AppColors.success,
                      ),
                      const SizedBox(width: 8),
                      _WeatherChip(
                        icon: Icons.water_drop_rounded,
                        label: '${weather.humidity.toStringAsFixed(0)}%',
                        color: AppColors.primary,
                      ),
                      const SizedBox(width: 8),
                      _WeatherChip(
                        icon: Icons.air_rounded,
                        label: '${weather.windSpeed.toStringAsFixed(0)} km/h',
                        color: AppColors.textSecondary,
                      ),
                    ],
                  ),
                  if (weather.rainfall > 0) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.warning.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: AppColors.warning.withOpacity(0.3),
                        ),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.umbrella_rounded,
                            color: AppColors.warning,
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Rain Alert: ${weather.rainfall.toStringAsFixed(1)} mm/hr expected. Consider indoor deliveries.',
                              style: AppTypography.bodySmall,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              );
            },
            loading: () =>
                const Center(child: CircularProgressIndicator(strokeWidth: 2)),
            error: (_, _) =>
                Text('Unable to load weather', style: AppTypography.bodySmall),
          ),
          const SizedBox(height: 12),
          trafficAsync.when(
            data: (traffic) {
              if (traffic.isEmpty) return const SizedBox.shrink();
              final congestion = traffic['congestion_percent'] as num? ?? 0;
              final isHigh = congestion > 50;
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: (isHigh ? AppColors.danger : AppColors.success)
                      .withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.traffic_rounded,
                      color: isHigh ? AppColors.danger : AppColors.success,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        isHigh
                            ? 'Heavy traffic: ${congestion.toStringAsFixed(0)}% congestion. Expect delays.'
                            : 'Traffic is clear: ${congestion.toStringAsFixed(0)}% congestion.',
                        style: AppTypography.bodySmall,
                      ),
                    ),
                  ],
                ),
              );
            },
            loading: () => const SizedBox.shrink(),
            error: (_, _) => const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}

class _WeatherChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;

  const _WeatherChip({
    required this.icon,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 4),
          Text(label, style: AppTypography.labelSmall.copyWith(color: color)),
        ],
      ),
    );
  }
}

class _NewsAlertsCard extends StatelessWidget {
  final Map<String, dynamic> news;

  const _NewsAlertsCard({required this.news});

  @override
  Widget build(BuildContext context) {
    final incidents = (news['incidents'] as List<dynamic>?) ?? [];
    final relevantIncidents = incidents
        .where((i) => i['is_trigger_relevant'] == true)
        .toList();

    if (incidents.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.warning.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.newspaper_rounded,
                  color: AppColors.warning,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Zone News & Alerts', style: AppTypography.titleSmall),
                    Text(
                      '${incidents.length} updates · ${relevantIncidents.length} may affect coverage',
                      style: AppTypography.labelSmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...incidents.take(3).map((incident) => _NewsItem(incident: incident)),
        ],
      ),
    );
  }
}

class _NewsItem extends StatelessWidget {
  final Map<String, dynamic> incident;

  const _NewsItem({required this.incident});

  @override
  Widget build(BuildContext context) {
    final isRelevant = incident['is_trigger_relevant'] == true;
    final category = incident['category'] as String? ?? 'news';
    final severity = incident['severity'] as String? ?? 'low';

    Color severityColor;
    switch (severity.toLowerCase()) {
      case 'high':
        severityColor = AppColors.danger;
        break;
      case 'medium':
        severityColor = AppColors.warning;
        break;
      default:
        severityColor = AppColors.success;
    }

    IconData categoryIcon;
    switch (category.toLowerCase()) {
      case 'traffic':
        categoryIcon = Icons.traffic_rounded;
        break;
      case 'weather':
        categoryIcon = Icons.cloud_rounded;
        break;
      case 'protest':
      case 'strike':
        categoryIcon = Icons.groups_rounded;
        break;
      case 'road_disruption':
        categoryIcon = Icons.warning_rounded;
        break;
      default:
        categoryIcon = Icons.article_rounded;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isRelevant
            ? severityColor.withOpacity(0.05)
            : AppColors.background,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isRelevant ? severityColor.withOpacity(0.2) : AppColors.border,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: severityColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Icon(categoryIcon, size: 16, color: severityColor),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  incident['headline'] as String? ?? 'News Update',
                  style: AppTypography.bodySmall.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Text(
                      category.toUpperCase(),
                      style: AppTypography.labelSmall.copyWith(
                        color: severityColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (isRelevant) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          'MAY TRIGGER CLAIM',
                          style: AppTypography.labelSmall.copyWith(
                            color: AppColors.primary,
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
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

class _PolicyHero extends StatelessWidget {
  final Policy policy;

  const _PolicyHero({required this.policy});

  @override
  Widget build(BuildContext context) {
    final progress = (policy.daysRemaining.clamp(0, 7) / 7);

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
            width: 140,
            height: 140,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 140,
                  height: 140,
                  child: CircularProgressIndicator(
                    value: progress,
                    strokeWidth: 10,
                    backgroundColor: AppColors.white.withOpacity(0.2),
                    valueColor: const AlwaysStoppedAnimation(AppColors.white),
                  ),
                ),
                Container(
                  width: 100,
                  height: 100,
                  alignment: Alignment.center,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        '${policy.daysRemaining}',
                        style: AppTypography.displayLarge.copyWith(
                          color: AppColors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 42,
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
