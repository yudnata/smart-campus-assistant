// ============================================================
// app.dart — Root widget
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'package:rag_akademik/features/chat/presentation/screens/chat_screen.dart';
import 'package:rag_akademik/features/chat/presentation/screens/admin_panel_screen.dart';
import 'package:rag_akademik/features/auth/presentation/screens/login_screen.dart';
import 'package:rag_akademik/features/auth/providers/auth_provider.dart';

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      child: MaterialApp(
        title: 'RAG Pedoman Akademik',
        debugShowCheckedModeBanner: false,
        themeMode: ThemeMode.light,
        theme: AppTheme.light,
        darkTheme: AppTheme.light,
        home: Consumer(
          builder: (context, ref, child) {
            final authState = ref.watch(authProvider);
            if (authState.isLoading) {
              return const Scaffold(
                  body: Center(child: CircularProgressIndicator()));
            }
            if (authState.isAuthenticated || authState.isGuest) {
              if (authState.user != null && authState.user!['is_admin'] == true) {
                return const AdminPanelScreen();
              }
              return const ChatScreen();
            }
            return const LoginScreen();
          },
        ),
      ),
    );
  }
}
