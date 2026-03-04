import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/theme.dart';
import '../../../../core/constants/constants.dart';
import '../../../../core/providers/providers.dart';
import '../../../../core/router/app_router.dart';
import '../../../../shared/models/models.dart';

/// Profile input screen
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isListening = false;

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  bool get _isValid =>
      _nameController.text.isNotEmpty &&
      _phoneController.text.length >= 10 &&
      _passwordController.text.length >= 6;

  void _simulateVoiceInput() {
    setState(() => _isListening = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        setState(() {
          _nameController.text = 'Ramesh Kumar';
          _phoneController.text = '9876543210';
          _isListening = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => context.go(AppRoutes.persona),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Progress
              _buildProgress(2, 4),

              const SizedBox(height: 32),

              // Title
              Text(
                AppStrings.profileTitle,
                style: AppTypography.displaySmall,
              ).animate().fadeIn(duration: 300.ms),

              const SizedBox(height: 8),

              Text(
                AppStrings.profileSubtitle,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.textSecondary,
                ),
              ).animate(delay: 100.ms).fadeIn(),

              const SizedBox(height: 32),

              // Voice input button
              GestureDetector(
                    onTap: _simulateVoiceInput,
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.secondary.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: AppColors.secondary.withOpacity(0.3),
                          style: BorderStyle.solid,
                        ),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            _isListening ? Icons.mic : Icons.mic_none_rounded,
                            color: AppColors.secondary,
                          ),
                          const SizedBox(width: 12),
                          Text(
                            _isListening
                                ? 'Listening...'
                                : 'Fill with Voice (Hindi/English)',
                            style: AppTypography.labelLarge.copyWith(
                              color: AppColors.secondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .animate(delay: 200.ms)
                  .fadeIn()
                  .scale(begin: const Offset(0.95, 0.95)),

              const SizedBox(height: 32),

              // Name field
              Text(
                'FULL NAME',
                style: AppTypography.labelSmall.copyWith(
                  color: AppColors.textSecondary,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _nameController,
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  hintText: 'e.g. Ramesh Kumar',
                  prefixIcon: const Icon(Icons.person_outline_rounded),
                  filled: true,
                  fillColor: AppColors.surface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                ),
              ).animate(delay: 300.ms).fadeIn().slideY(begin: 0.1),

              const SizedBox(height: 24),

              // Phone field
              Text(
                'PHONE (UPI LINKED)',
                style: AppTypography.labelSmall.copyWith(
                  color: AppColors.textSecondary,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  hintText: 'e.g. 9876543210',
                  prefixIcon: const Icon(Icons.phone_android_rounded),
                  filled: true,
                  fillColor: AppColors.surface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                ),
              ).animate(delay: 400.ms).fadeIn().slideY(begin: 0.1),

              const SizedBox(height: 24),

              Text(
                'CREATE PASSWORD',
                style: AppTypography.labelSmall.copyWith(
                  color: AppColors.textSecondary,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _passwordController,
                obscureText: true,
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  hintText: 'Min 6 characters',
                  prefixIcon: const Icon(Icons.lock_outline_rounded),
                  filled: true,
                  fillColor: AppColors.surface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                ),
              ).animate(delay: 450.ms).fadeIn().slideY(begin: 0.1),

              const SizedBox(height: 48),

              // Continue button
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _isValid
                      ? () {
                          final onboarding = ref.read(onboardingProvider);
                          ref
                              .read(onboardingProvider.notifier)
                              .setProfile(
                                name: _nameController.text.trim(),
                                phone: _phoneController.text.trim(),
                                password: _passwordController.text,
                              );
                          ref.read(onboardingProvider.notifier).setZone(
                            Zone(
                              id: 'route_pending',
                              name: 'Route risk at delivery start',
                              city: 'Dynamic route',
                              state: null,
                              country: 'IN',
                              latitude: 0,
                              longitude: 0,
                              radiusKm: 0,
                              riskLevel: 'medium',
                              basePremiumFactor: onboarding.persona == 'qcommerce'
                                  ? 1.15
                                  : 1.1,
                              isActive: true,
                            ),
                          );
                          context.go(AppRoutes.review);
                        }
                      : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    disabledBackgroundColor: AppColors.border,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: Text(
                    AppStrings.continueBtn,
                    style: AppTypography.buttonLarge.copyWith(
                      color: _isValid
                          ? AppColors.white
                          : AppColors.textTertiary,
                    ),
                  ),
                ),
              ).animate(delay: 500.ms).fadeIn(),
            ],
          ),
        ),
      ),
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
