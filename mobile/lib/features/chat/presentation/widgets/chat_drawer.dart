// ============================================================
// features/chat/presentation/widgets/chat_drawer.dart
// Sidebar Drawer untuk navigasi, riwayat chat, dan profil
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_theme.dart';
import '../screens/search_chat_screen.dart';
import '../../../auth/providers/auth_provider.dart';
import '../providers/history_provider.dart';
import '../providers/chat_provider.dart';
import '../../../auth/presentation/screens/login_screen.dart';
import '../screens/admin_panel_screen.dart';

class ChatDrawer extends ConsumerWidget {
  const ChatDrawer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final historyState = ref.watch(historyProvider);

    return Drawer(
      backgroundColor: AppTheme.surfaceLight,
      elevation: 16,
      shadowColor: Colors.black.withValues(alpha: 0.1),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.only(
          topRight: Radius.circular(24),
          bottomRight: Radius.circular(24),
        ),
      ),
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header / App Branding
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(
                children: [
                  Icon(
                    Icons.school_rounded,
                    color: AppTheme.accentPrimary,
                    size: 26,
                  ),
                  SizedBox(width: 10),
                  Text(
                    'Smart Campus Assistant',
                    style: TextStyle(
                      fontFamily: 'Quicksand',
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                ],
              ),
            ),

            const Divider(height: 1, indent: 20, endIndent: 20),

            // Action: New Chat & Search Chat
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  // New Chat Button
                  Container(
                    width: double.infinity,
                    height: 48,
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceLight,
                      borderRadius: BorderRadius.circular(24),
                      border:
                          Border.all(color: AppTheme.surfaceBorder, width: 1.5),
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(24),
                        onTap: () {
                          ref.read(chatProvider.notifier).clearChat();
                          Navigator.pop(context); // Close drawer
                        },
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.add_rounded,
                                color: AppTheme.textPrimary, size: 20),
                            SizedBox(width: 8),
                            Text(
                              'Obrolan Baru',
                              style: TextStyle(
                                fontFamily: 'Quicksand',
                                fontWeight: FontWeight.w600,
                                color: AppTheme.textPrimary,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Search Chat Button
                  if (authState.isAuthenticated)
                    Container(
                      width: double.infinity,
                      height: 48,
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceLight,
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                            color: AppTheme.surfaceBorder, width: 1.5),
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          borderRadius: BorderRadius.circular(24),
                          onTap: () {
                            Navigator.pop(context);
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                  builder: (context) =>
                                      const SearchChatScreen()),
                            );
                          },
                          child: const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.search_rounded,
                                  color: AppTheme.textPrimary, size: 20),
                              SizedBox(width: 8),
                              Text(
                                'Cari Obrolan',
                                style: TextStyle(
                                  fontFamily: 'Quicksand',
                                  fontWeight: FontWeight.w600,
                                  color: AppTheme.textPrimary,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),

                  // Panel Admin Button (Hanya tampil jika user adalah admin)
                  if (authState.isAuthenticated && authState.user != null && authState.user!['is_admin'] == true) ...[
                    const SizedBox(height: 12),
                    Container(
                      width: double.infinity,
                      height: 48,
                      decoration: BoxDecoration(
                        color: AppTheme.accentPrimary.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                            color: AppTheme.accentPrimary.withValues(alpha: 0.3), width: 1.5),
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          borderRadius: BorderRadius.circular(24),
                          onTap: () {
                            Navigator.pop(context); // close drawer
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => const AdminPanelScreen(),
                              ),
                            );
                          },
                          child: const Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.admin_panel_settings_rounded,
                                  color: AppTheme.accentPrimary, size: 20),
                              SizedBox(width: 8),
                              Text(
                                'Panel Admin',
                                style: TextStyle(
                                  fontFamily: 'Quicksand',
                                  fontWeight: FontWeight.w600,
                                  color: AppTheme.accentPrimary,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),

            // Recent Chat label
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Text(
                'OBROLAN TERBARU',
                style: TextStyle(
                  fontFamily: 'Quicksand',
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textMuted,
                  letterSpacing: 0.8,
                ),
              ),
            ),

            // Recent Chats List
            Expanded(
              child: authState.isAuthenticated
                  ? (historyState.isLoading &&
                          historyState.conversations.isEmpty)
                      ? const Center(child: CircularProgressIndicator())
                      : historyState.conversations.isEmpty
                          ? const Center(
                              child: Text(
                                'Belum ada obrolan.',
                                style: TextStyle(
                                  fontFamily: 'Quicksand',
                                  color: AppTheme.textMuted,
                                ),
                              ),
                            )
                          : ListView.builder(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 12),
                              itemCount: historyState.conversations.length,
                              itemBuilder: (context, index) {
                                final conv = historyState.conversations[index];
                                final isActive = conv['id'] ==
                                    historyState.activeConversationId;
                                return Container(
                                  margin: const EdgeInsets.only(bottom: 4),
                                  decoration: BoxDecoration(
                                    color: isActive
                                        ? AppTheme.accentPrimary
                                            .withValues(alpha: 0.1)
                                        : Colors.transparent,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: ListTile(
                                    dense: true,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    leading: Icon(
                                      Icons.chat_bubble_outline_rounded,
                                      color: isActive
                                          ? AppTheme.accentPrimary
                                          : AppTheme.textSecondary,
                                      size: 16,
                                    ),
                                    title: Text(
                                      conv['title'] ?? 'Obrolan',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        fontFamily: 'Quicksand',
                                        fontSize: 13,
                                        fontWeight: isActive
                                            ? FontWeight.bold
                                            : FontWeight.w500,
                                        color: isActive
                                            ? AppTheme.accentPrimary
                                            : AppTheme.textSecondary,
                                      ),
                                    ),
                                    onTap: () {
                                      Navigator.pop(context);
                                      ref
                                          .read(chatProvider.notifier)
                                          .loadConversation(conv['id']);
                                    },
                                  ),
                                );
                              },
                            )
                  : const Center(
                      child: Text(
                        'Masuk untuk melihat riwayat.',
                        style: TextStyle(
                          fontFamily: 'Quicksand',
                          color: AppTheme.textMuted,
                        ),
                      ),
                    ),
            ),

            // User Profile Section at bottom
            const Divider(height: 1),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              color: AppTheme.surfaceLight,
              child: Row(
                children: [
                  // Placeholder Profile Image
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: AppTheme.accentPrimary.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: AppTheme.accentPrimary.withValues(alpha: 0.2),
                        width: 1.5,
                      ),
                    ),
                    child: Center(
                      child: Text(
                        authState.isAuthenticated && authState.user != null
                            ? (authState.user!['name'] as String)
                                .substring(0, 1)
                                .toUpperCase()
                            : 'G',
                        style: const TextStyle(
                          fontFamily: 'Quicksand',
                          fontWeight: FontWeight.bold,
                          color: AppTheme.accentPrimary,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Name and detail
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          authState.isAuthenticated && authState.user != null
                              ? authState.user!['name']
                              : 'Tamu (Guest)',
                          style: const TextStyle(
                            fontFamily: 'Quicksand',
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                        if (authState.isAuthenticated && authState.user != null)
                          Text(
                            authState.user!['email'],
                            style: const TextStyle(
                              fontFamily: 'Quicksand',
                              fontSize: 11,
                              color: AppTheme.textMuted,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                  ),
                  // Action button: Logout or Login
                  if (authState.isAuthenticated)
                    IconButton(
                      icon: const Icon(Icons.logout_rounded,
                          color: AppTheme.errorColor, size: 20),
                      onPressed: () {
                        ref.read(authProvider.notifier).logout();
                        Navigator.pop(context);
                      },
                    )
                  else
                    TextButton(
                      onPressed: () {
                        Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) => const LoginScreen()));
                      },
                      child: const Text('Masuk',
                          style: TextStyle(
                              fontFamily: 'Quicksand',
                              fontWeight: FontWeight.bold)),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
