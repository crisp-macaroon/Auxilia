import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/router/app_router.dart';

/// Legacy route placeholder: onboarding no longer collects zone/delivery point.
class ZoneScreen extends StatelessWidget {
  const ZoneScreen({super.key});

  @override
  Widget build(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (context.mounted) {
        context.go(AppRoutes.review);
      }
    });

    return const Scaffold(body: SizedBox.shrink());
  }
}
