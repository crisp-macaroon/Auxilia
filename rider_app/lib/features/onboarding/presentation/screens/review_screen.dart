import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';

import '../../../../core/providers/providers.dart';
import '../../../../core/theme/theme.dart';
import '../../../../core/router/app_router.dart';

/// Policy review and payment screen
class ReviewScreen extends ConsumerStatefulWidget {
  const ReviewScreen({super.key});

  @override
  ConsumerState<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends ConsumerState<ReviewScreen> {
  bool _isProcessing = false;
  int _pointsToRedeem = 0;
  late final Razorpay _razorpay;
  Map<String, dynamic>? _pendingOrder;
  String? _pendingRiderId;

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

  void _processPayment() async {
    setState(() => _isProcessing = true);
    final onboarding = ref.read(onboardingProvider);
    final api = ref.read(apiServiceProvider);

    final riderResponse = await ref
        .read(onboardingProvider.notifier)
        .register();
    if (!mounted) return;

    if (!riderResponse.success || riderResponse.data == null) {
      setState(() => _isProcessing = false);
      _showError(riderResponse.error ?? 'Failed to create rider profile');
      return;
    }

    _pendingRiderId = riderResponse.data!.rider.id;

    final orderResponse = await api.createPolicyPaymentOrder(
      flowType: 'new_policy',
      riderId: riderResponse.data!.rider.id,
      zoneId: onboarding.zoneId!,
      persona: onboarding.persona!,
      durationDays: 7,
      pointsToRedeem: _pointsToRedeem,
    );

    if (!mounted) return;

    if (!orderResponse.success || orderResponse.data == null) {
      setState(() => _isProcessing = false);
      _showError(orderResponse.error ?? 'Failed to start payment');
      return;
    }

    _pendingOrder = orderResponse.data;

    if ((orderResponse.data!['checkout_mode'] ?? 'sandbox') == 'sandbox') {
      await _confirmPolicyPayment(
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
      'description': 'Weekly rider protection plan',
      'order_id': orderResponse.data!['order_id'],
      'prefill': orderResponse.data!['prefill'] ?? {},
      'theme': {'color': '#F97316'},
    });
  }

  Future<void> _confirmPolicyPayment({
    required String orderId,
    required String paymentId,
    String? signature,
  }) async {
    final api = ref.read(apiServiceProvider);
    final onboarding = ref.read(onboardingProvider);
    final riderId = _pendingRiderId;

    if (_pendingOrder == null || riderId == null) {
      if (mounted) {
        setState(() => _isProcessing = false);
        _showError('Missing payment session. Please try again.');
      }
      return;
    }

    final policyResponse = await api.confirmPolicyPayment(
      flowType: 'new_policy',
      orderId: orderId,
      paymentId: paymentId,
      signature: signature,
      riderId: riderId,
      zoneId: onboarding.zoneId!,
      persona: onboarding.persona!,
      durationDays: 7,
      pointsToRedeem: _pointsToRedeem,
    );

    if (!mounted) return;

    if (!policyResponse.success) {
      setState(() => _isProcessing = false);
      final errorMessage =
          policyResponse.error ??
          'Payment verified but policy activation failed';
      if (errorMessage.contains('Invalid Razorpay signature')) {
        _showError(
          'Payment was received but server verification failed (signature mismatch). Check Razorpay key/secret config and retry.',
        );
      } else {
        _showError(errorMessage);
      }
      return;
    }

    ref.invalidate(currentRiderProvider);
    ref.invalidate(activePolicyProvider);
    ref.invalidate(latestPolicyProvider);
    ref.invalidate(claimsProvider);
    ref.invalidate(claimsSummaryProvider);
    ref.invalidate(triggersProvider);
    ref.read(onboardingProvider.notifier).reset();

    setState(() => _isProcessing = false);

    context.go(AppRoutes.success);
  }

  void _handlePaymentSuccess(PaymentSuccessResponse response) {
    final fallbackOrderId = _pendingOrder?['order_id'] as String?;
    final orderId = response.orderId ?? fallbackOrderId;
    final paymentId = response.paymentId;
    final signature = response.signature;

    if (orderId == null || paymentId == null || paymentId.isEmpty) {
      if (mounted) {
        setState(() => _isProcessing = false);
        _showError(
          'Payment completed but verification payload is incomplete. Please retry once.',
        );
      }
      return;
    }

    if (signature == null || signature.isEmpty) {
      if (mounted) {
        setState(() => _isProcessing = false);
        _showError(
          'Payment succeeded but signature was missing, so we could not verify it. Please retry.',
        );
      }
      return;
    }

    _confirmPolicyPayment(
      orderId: orderId,
      paymentId: paymentId,
      signature: signature,
    );
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    if (!mounted) return;
    setState(() => _isProcessing = false);
    final code = response.code != null ? ' (${response.code})' : '';
    final message = response.message ?? 'Payment was cancelled';
    _showError('Razorpay payment failed$code: $message');
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    if (!mounted) return;
    setState(() => _isProcessing = false);
    _showError(
      '${response.walletName ?? 'External wallet'} is not supported for this checkout',
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final quotePreviewAsync = ref.watch(quotePreviewProvider);
    const basePremium = 99;
    const gstRate = 0.18;
    final gstAmount = (basePremium * gstRate).round();
    final total = basePremium + gstAmount;
    final rider = ref.watch(currentRiderProvider).valueOrNull;
    final loyaltyPoints = rider?.loyaltyPoints ?? 0;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.go(AppRoutes.profile),
        ),
      ),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) => SingleChildScrollView(
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight),
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Progress
                    _buildProgress(4, 4),

                    const SizedBox(height: 32),

                    Text(
                      'Your Weekly Policy',
                      style: AppTypography.displaySmall,
                    ).animate().fadeIn(duration: 300.ms),

                    const SizedBox(height: 8),

                    Text(
                      'Fixed weekly base premium for every rider.',
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ).animate(delay: 100.ms).fadeIn(),

                    const SizedBox(height: 32),

                    // Premium breakdown card
                    Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                AppColors.warning.withOpacity(0.1),
                                AppColors.warning.withOpacity(0.05),
                              ],
                            ),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: AppColors.warning.withOpacity(0.2),
                            ),
                          ),
                          child: Column(
                            children: [
                              _buildPremiumRow(
                                'Base premium (1 week)',
                                'Rs $basePremium',
                              ),
                              const Divider(height: 24),
                              _buildPremiumRow('GST (18%)', '+ Rs $gstAmount'),
                              const Divider(height: 24),
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    'Total / week (incl. tax)',
                                    style: AppTypography.titleMedium.copyWith(
                                      color: AppColors.warning,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  Text(
                                    'Rs $total',
                                    style: AppTypography.displaySmall.copyWith(
                                      color: AppColors.warning,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        )
                        .animate(delay: 200.ms)
                        .fadeIn()
                        .scale(begin: const Offset(0.95, 0.95)),

                    const SizedBox(height: 24),

                    // Benefits card
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withOpacity(0.05),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: AppColors.primary.withOpacity(0.2),
                        ),
                      ),
                      child: Column(
                        children: [
                          _buildBenefitRow(
                            Icons.autorenew,
                            'Auto-renews every Sunday via Razorpay',
                          ),
                          const SizedBox(height: 12),
                          _buildBenefitRow(
                            Icons.shield,
                            'Coverage activates instantly for live parametric events',
                          ),
                          const SizedBox(height: 12),
                          _buildBenefitRow(
                            Icons.verified,
                            'Policy hash stored on blockchain',
                          ),
                        ],
                      ),
                    ).animate(delay: 300.ms).fadeIn(),

                    const SizedBox(height: 12),
                    if (loyaltyPoints > 0)
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: AppColors.success.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: AppColors.success.withOpacity(0.25),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Loyalty points',
                              style: AppTypography.titleSmall,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Available: $loyaltyPoints points',
                              style: AppTypography.bodySmall.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                            const SizedBox(height: 10),
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    'Redeem now',
                                    style: AppTypography.labelMedium,
                                  ),
                                ),
                                Switch(
                                  value: _pointsToRedeem > 0,
                                  onChanged: (on) {
                                    setState(() {
                                      _pointsToRedeem = on ? loyaltyPoints : 0;
                                    });
                                  },
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: AppColors.background,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppColors.border),
                              ),
                              child: Text(
                                'Formula: 1 point = Rs 0.25, redeem up to 75% of gross premium.\nNo-claim week earns loyalty points.',
                                style: AppTypography.bodySmall.copyWith(
                                  color: AppColors.textSecondary,
                                  height: 1.4,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                    const SizedBox(height: 16),
                    quotePreviewAsync.when(
                      data: (quote) {
                        if (quote.isEmpty) return const SizedBox.shrink();
                        final expected =
                            (quote['expected_value']
                                as Map<String, dynamic>?) ??
                            {};
                        final regret =
                            (quote['regret_protection']
                                as Map<String, dynamic>?) ??
                            {};

                        return Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppColors.secondary.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: AppColors.secondary.withOpacity(0.2),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Expected value',
                                style: AppTypography.titleSmall,
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'Estimated payout Rs ${((expected['expected_payout'] ?? 0) as num).toStringAsFixed(0)} vs weekly premium Rs ${((quote['weekly_premium'] ?? 0) as num).toStringAsFixed(0)}',
                                style: AppTypography.bodySmall.copyWith(
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Loyalty protection: earn ${((regret['loyalty_points_if_no_trigger'] ?? 0) as num).toStringAsFixed(0)} points if no trigger this week.',
                                style: AppTypography.bodySmall.copyWith(
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                      loading: () => const SizedBox.shrink(),
                      error: (_, _) => const SizedBox.shrink(),
                    ),

                    const SizedBox(height: 16),

                    SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: ElevatedButton(
                        onPressed: _isProcessing ? null : _processPayment,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                        ),
                        child: _isProcessing
                            ? Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation(
                                        AppColors.white,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Text(
                                    'Opening Razorpay...',
                                    style: AppTypography.buttonMedium.copyWith(
                                      color: AppColors.white,
                                    ),
                                  ),
                                ],
                              )
                            : Text(
                                'Activate for Rs $total',
                                style: AppTypography.buttonLarge.copyWith(
                                  color: AppColors.white,
                                ),
                              ),
                      ),
                    ).animate(delay: 400.ms).fadeIn(),

                    const SizedBox(height: 10),

                    OutlinedButton(
                      onPressed: _isProcessing
                          ? null
                          : () {
                              ref
                                  .read(onboardingProvider.notifier)
                                  .setPurchaseLater(true);
                              context.go(AppRoutes.home);
                            },
                      child: const Text('Purchase later and continue'),
                    ),

                    const SizedBox(height: 10),
                    Text(
                      'Tax is included in checkout total. Policy premium remains Rs 99/week.',
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),

                    const SizedBox(height: 16),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPremiumRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
        Text(
          value,
          style: AppTypography.labelLarge.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
      ],
    );
  }

  Widget _buildBenefitRow(IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, size: 18, color: AppColors.primary),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            text,
            style: AppTypography.bodySmall.copyWith(color: AppColors.primary),
          ),
        ),
      ],
    );
  }

  Widget _buildProgress(int current, int total) {
    return Row(
      children: List.generate(total, (index) {
        final isActive = index < current;
        return Expanded(
          child: Container(
            margin: EdgeInsets.only(right: index < total - 1 ? 8 : 0),
            height: 4,
            decoration: BoxDecoration(
              color: isActive ? AppColors.primary : AppColors.border,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        );
      }),
    );
  }
}
