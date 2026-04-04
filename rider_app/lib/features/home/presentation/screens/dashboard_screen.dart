import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../../../../core/providers/providers.dart';
import '../../../../core/theme/theme.dart';
import '../../../../shared/models/models.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(locationSyncProvider);
    final riderAsync = ref.watch(currentRiderProvider);
    final policyAsync = ref.watch(activePolicyProvider);
    final latestPolicyAsync = ref.watch(latestPolicyProvider);
    final claimsSummaryAsync = ref.watch(claimsSummaryProvider);
    final triggersAsync = ref.watch(triggersProvider);
    final locationAsync = ref.watch(locationTrackingProvider);
    final heatmapAsync = ref.watch(zoneHeatmapProvider);
    final architectureAsync = ref.watch(architectureProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(currentRiderProvider);
            ref.invalidate(activePolicyProvider);
            ref.invalidate(latestPolicyProvider);
            ref.invalidate(claimsSummaryProvider);
            ref.invalidate(triggersProvider);
          },
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              riderAsync
                  .when(
                    data: (rider) {
                      final name = rider?.name.split(' ').first ?? 'Rider';
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Hi, $name', style: AppTypography.displaySmall),
                          const SizedBox(height: 8),
                          Text(
                            'Your parametric shield is watching the road in real time.',
                            style: AppTypography.bodyMedium.copyWith(
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      );
                    },
                    loading: () => const _HeaderSkeleton(),
                    error: (_, _) => Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Welcome back', style: AppTypography.displaySmall),
                        const SizedBox(height: 8),
                        Text(
                          'Connect the backend to see your live rider profile.',
                          style: AppTypography.bodyMedium.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  )
                  .animate()
                  .fadeIn(),
              const SizedBox(height: 24),
              _LocationStatusCard(locationAsync: locationAsync),
              const SizedBox(height: 16),
              _DeliveryCheckInCard(),
              const SizedBox(height: 24),
              policyAsync.when(
                data: (policy) {
                  if (policy != null) {
                    return _ShieldCard(daysLeft: policy.daysRemaining);
                  }

                  final rider = riderAsync.valueOrNull;
                  final latestPolicy = latestPolicyAsync.valueOrNull;
                  if (rider != null && latestPolicy != null) {
                    return const _EmptyCard(
                      title: 'Policy expired',
                      subtitle: 'You are onboarded. Renew coverage from the Policy tab.',
                    );
                  }

                  return const _EmptyCard(
                    title: 'No active policy yet',
                    subtitle: 'Finish onboarding to activate your coverage.',
                  );
                },
                loading: () => const _CardSkeleton(height: 220),
                error: (_, _) => const _EmptyCard(
                  title: 'No active policy yet',
                  subtitle: 'Finish onboarding to activate your coverage.',
                ),
              ),
              const SizedBox(height: 24),
              heatmapAsync.when(
                data: (heatmap) => _HeatmapCard(data: heatmap),
                loading: () => const _CardSkeleton(height: 180),
                error: (_, _) => const _EmptyCard(
                  title: 'Heatmap unavailable',
                  subtitle: 'Start backend to render dynamic zone heat.',
                ),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: claimsSummaryAsync.when(
                      data: (summary) => _MetricCard(
                        title: 'Settled Claims',
                        value: '${summary['settled'] ?? summary['paid'] ?? 0}',
                        accent: AppColors.success,
                      ),
                      loading: () => const _CardSkeleton(height: 110),
                      error: (_, _) => const _MetricCard(
                        title: 'Settled Claims',
                        value: '0',
                        accent: AppColors.success,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: claimsSummaryAsync.when(
                      data: (summary) => _MetricCard(
                        title: 'Protected',
                        value:
                            'Rs ${((summary['amount'] ?? 0) as num).toStringAsFixed(0)}',
                        accent: AppColors.primary,
                      ),
                      loading: () => const _CardSkeleton(height: 110),
                      error: (_, _) => const _MetricCard(
                        title: 'Protected',
                        value: 'Rs 0',
                        accent: AppColors.primary,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text('Live trigger monitor', style: AppTypography.titleLarge),
              const SizedBox(height: 8),
              Text(
                'Weather, traffic, and incident signals from your zone.',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 16),
              triggersAsync.when(
                data: (triggers) {
                  if (triggers.isEmpty) {
                    return const _EmptyCard(
                      title: 'No active zone signals',
                      subtitle:
                          'Once trigger checks run, they will appear here.',
                    );
                  }

                  return Column(
                    children: triggers
                        .map(
                          (trigger) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: _TriggerCard(trigger: trigger),
                          ),
                        )
                        .toList(),
                  );
                },
                loading: () => const _CardSkeleton(height: 200),
                error: (_, _) => const _EmptyCard(
                  title: 'Trigger feed unavailable',
                  subtitle: 'Start the backend to load live monitoring data.',
                ),
              ),
              const SizedBox(height: 24),
              architectureAsync.when(
                data: (arch) => _FlowCard(data: arch),
                loading: () => const _CardSkeleton(height: 160),
                error: (_, _) => const SizedBox.shrink(),
              ),
              const SizedBox(height: 100),
            ],
          ),
        ),
      ),
    );
  }
}

class _LocationStatusCard extends ConsumerWidget {
  final AsyncValue<Position> locationAsync;

  const _LocationStatusCard({required this.locationAsync});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final movement = ref.watch(movementProvider);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: locationAsync.when(
        data: (position) => Row(
          children: [
            const Icon(Icons.my_location_rounded, color: AppColors.success),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                movement.isMoving
                    ? 'Moving (${movement.movedMeters.toStringAsFixed(0)}m): ${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)}'
                    : 'Tracking active: ${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)}',
                style: AppTypography.bodySmall,
              ),
            ),
          ],
        ),
        loading: () => Row(
          children: [
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 10),
            Text(
              'Requesting location permission...',
              style: AppTypography.bodySmall,
            ),
          ],
        ),
        error: (error, _) => InkWell(
          onTap: () async {
            // Open settings and then refresh
            await Geolocator.openAppSettings();
            ref.invalidate(locationTrackingProvider);
          },
          child: Row(
            children: [
              const Icon(Icons.location_off_rounded, color: AppColors.warning),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Location permission required',
                      style: AppTypography.bodySmall.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Tap to open settings and enable location access',
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppColors.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}

class _DeliveryCheckInCard extends ConsumerStatefulWidget {
  const _DeliveryCheckInCard();

  @override
  ConsumerState<_DeliveryCheckInCard> createState() =>
      _DeliveryCheckInCardState();
}

class _DeliveryCheckInCardState extends ConsumerState<_DeliveryCheckInCard> {
  final _orderController = TextEditingController();
  final _latController = TextEditingController();
  final _lonController = TextEditingController();
  String _result = '';
  bool _loading = false;

  @override
  void dispose() {
    _orderController.dispose();
    _latController.dispose();
    _lonController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _loading = true);
    final rider = await ref.read(currentRiderProvider.future);
    if (rider == null) {
      setState(() {
        _loading = false;
        _result = 'No rider session found';
      });
      return;
    }

    final api = ref.read(apiServiceProvider);
    Position? location;
    try {
      location = await ref.read(locationTrackingProvider.future);
    } catch (_) {
      location = null;
    }

    final response = await api.deliveryCheckIn(
      riderId: rider.id,
      orderId: _orderController.text.trim().isEmpty
          ? null
          : _orderController.text.trim(),
      deliveryLat: double.tryParse(_latController.text.trim()) ?? 0,
      deliveryLon: double.tryParse(_lonController.text.trim()) ?? 0,
      riderLat: location == null ? null : location.latitude,
      riderLon: location == null ? null : location.longitude,
    );

    setState(() {
      _loading = false;
      _result = response.success
          ? 'Zone: ${response.data?['assigned_zone_name']} | Eligible: ${response.data?['is_delivery_in_coverage_zone']} | Risk: ${response.data?['computed_risk_score']}'
          : (response.error ?? 'Check-in failed');
    });
  }

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
          Text(
            'Delivery Check-in (Insurance Validation)',
            style: AppTypography.titleSmall,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _orderController,
            decoration: const InputDecoration(labelText: 'Order ID (optional)'),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _latController,
                  decoration: const InputDecoration(
                    labelText: 'Delivery Latitude',
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextField(
                  controller: _lonController,
                  decoration: const InputDecoration(
                    labelText: 'Delivery Longitude',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _loading ? null : _submit,
              child: Text(_loading ? 'Checking...' : 'Validate Delivery Zone'),
            ),
          ),
          if (_result.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              _result,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _HeatmapCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _HeatmapCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final points = (data['points'] as List<dynamic>? ?? []);

    // Group by city for better display
    final Map<String, List<dynamic>> byCity = {};
    for (var point in points.take(12)) {
      final city = point['city'] as String? ?? 'Unknown';
      byCity.putIfAbsent(city, () => []).add(point);
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
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(
                  Icons.map_rounded,
                  color: AppColors.primary,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Zone Risk Heatmap', style: AppTypography.titleSmall),
                  Text(
                    '${points.length} zones monitored',
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Risk legend
          Row(
            children: [
              _legendDot(AppColors.success, 'Low'),
              const SizedBox(width: 12),
              _legendDot(AppColors.warning, 'Medium'),
              const SizedBox(width: 12),
              _legendDot(AppColors.danger, 'High'),
            ],
          ),
          const SizedBox(height: 12),
          // Zone grid
          ...byCity.entries
              .take(3)
              .map(
                (entry) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry.key,
                        style: AppTypography.labelMedium.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: entry.value.take(4).map((point) {
                          final score =
                              (point['heat_score'] as num?)?.toDouble() ?? 0.0;
                          final color = score >= 0.7
                              ? AppColors.danger
                              : score >= 0.4
                              ? AppColors.warning
                              : AppColors.success;
                          return Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: color.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: color.withOpacity(0.3)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  width: 8,
                                  height: 8,
                                  decoration: BoxDecoration(
                                    color: color,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  '${point['zone_name']}',
                                  style: AppTypography.labelSmall,
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                ),
              ),
        ],
      ),
    );
  }

  Widget _legendDot(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: AppTypography.labelSmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}

class _FlowCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const _FlowCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final pipeline = (data['pipeline'] as List<dynamic>? ?? []).cast<String>();
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
          Text('Project Flow', style: AppTypography.titleSmall),
          const SizedBox(height: 8),
          ...pipeline
              .take(6)
              .map(
                (step) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('-> $step', style: AppTypography.bodySmall),
                ),
              ),
        ],
      ),
    );
  }
}

class _ShieldCard extends StatelessWidget {
  final int daysLeft;

  const _ShieldCard({required this.daysLeft});

  @override
  Widget build(BuildContext context) {
    // Weekly model: 7 days max
    final progress = daysLeft <= 0 ? 0.0 : (daysLeft.clamp(0, 7) / 7);

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: AppColors.primaryGradient,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withOpacity(0.24),
            blurRadius: 24,
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
                        '$daysLeft',
                        style: AppTypography.displayLarge.copyWith(
                          color: AppColors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 42,
                        ),
                      ),
                      Text(
                        'days left',
                        style: AppTypography.labelSmall.copyWith(
                          color: AppColors.white.withOpacity(0.84),
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
              color: AppColors.white.withOpacity(0.16),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              daysLeft > 0 ? 'SHIELD ACTIVE' : 'RENEW REQUIRED',
              style: AppTypography.labelSmall.copyWith(
                color: AppColors.white,
                fontWeight: FontWeight.w700,
                letterSpacing: 1,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final Color accent;

  const _MetricCard({
    required this.title,
    required this.value,
    required this.accent,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: AppTypography.displaySmall.copyWith(
              color: accent,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _TriggerCard extends StatelessWidget {
  final TriggerStatusModel trigger;

  const _TriggerCard({required this.trigger});

  @override
  Widget build(BuildContext context) {
    final color = trigger.isActive ? AppColors.warning : AppColors.success;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: color.withOpacity(0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(Icons.sensors_rounded, color: color),
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
                const SizedBox(height: 4),
                Text(
                  'Current ${trigger.currentValue.toStringAsFixed(1)} / Threshold ${trigger.threshold.toStringAsFixed(1)}',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color.withOpacity(0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              trigger.statusLabel,
              style: AppTypography.labelSmall.copyWith(
                color: color,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyCard extends StatelessWidget {
  final String title;
  final String subtitle;

  const _EmptyCard({required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTypography.titleSmall),
          const SizedBox(height: 6),
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

class _CardSkeleton extends StatelessWidget {
  final double height;

  const _CardSkeleton({required this.height});

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

class _HeaderSkeleton extends StatelessWidget {
  const _HeaderSkeleton();

  @override
  Widget build(BuildContext context) {
    return const _CardSkeleton(height: 70);
  }
}
