import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/providers/providers.dart';
import '../../../../core/theme/theme.dart';
import '../../../../shared/models/models.dart';

class DeliveryHistoryScreen extends ConsumerWidget {
  const DeliveryHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyAsync = ref.watch(deliveryHistoryProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Delivery History'),
        actions: [
          IconButton(
            onPressed: () => ref.invalidate(deliveryHistoryProvider),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: historyAsync.when(
        data: (items) {
          if (items.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'No deliveries yet. Use check-in on dashboard to record trips.',
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.textSecondary,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              final item = items[index];
              return _HistoryTile(item: item);
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => Center(
          child: Text(
            'Unable to load delivery history.',
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ),
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  final DeliveryHistoryItem item;

  const _HistoryTile({required this.item});

  @override
  Widget build(BuildContext context) {
    final created = item.createdAt;
    final hh = created.hour.toString().padLeft(2, '0');
    final mm = created.minute.toString().padLeft(2, '0');
    final date =
        '${created.day.toString().padLeft(2, '0')}/${created.month.toString().padLeft(2, '0')}/${created.year}';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                item.isDeliveryInCoverageZone
                    ? Icons.check_circle_outline
                    : Icons.warning_amber_rounded,
                color: item.isDeliveryInCoverageZone
                    ? AppColors.success
                    : AppColors.warning,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  item.assignedZoneName ?? item.assignedZoneId,
                  style: AppTypography.labelLarge,
                ),
              ),
              Text(
                '$date  $hh:$mm',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _chip(
                'Risk ${(item.computedRiskScore * 100).toStringAsFixed(0)}%',
              ),
              _chip('Weather ${(item.weatherRisk * 100).toStringAsFixed(0)}%'),
              _chip('Traffic ${(item.trafficRisk * 100).toStringAsFixed(0)}%'),
              _chip(
                'Incident ${(item.incidentRisk * 100).toStringAsFixed(0)}%',
              ),
              if (item.orderId != null && item.orderId!.isNotEmpty)
                _chip('Order ${item.orderId}'),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            item.eligibilityReason,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _chip(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.border),
      ),
      child: Text(text, style: AppTypography.bodySmall),
    );
  }
}
