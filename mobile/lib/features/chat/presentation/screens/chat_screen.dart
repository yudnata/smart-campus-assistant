// ============================================================
// features/chat/presentation/screens/chat_screen.dart
// Main chat screen — menggabungkan semua widget chat
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../providers/chat_provider.dart';
import '../providers/voice_provider.dart';
import '../../domain/models/chat_message.dart';
import '../widgets/message_bubble.dart';
import '../widgets/chat_input.dart';
import '../widgets/chat_drawer.dart';
import '../../../../core/theme/app_theme.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 350),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final chatNotifier = ref.read(chatProvider.notifier);

    // Scroll ke bawah saat pesan baru masuk
    ref.listen(chatProvider, (prev, next) {
      if (next.messages.isNotEmpty) {
        if (prev?.messages.length != next.messages.length) {
          _scrollToBottom();
        }
      }
    });

    return Scaffold(
      backgroundColor: AppTheme.backgroundLight,
      appBar: _buildAppBar(context, chatNotifier),
      drawer: const ChatDrawer(),
      body: Column(
        children: [
          // Pesan list
          Expanded(
            child: chatState.messages.isEmpty
                ? _EmptyState()
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.only(top: 12, bottom: 8),
                    itemCount: chatState.messages.length,
                    itemBuilder: (context, index) {
                      final msg = chatState.messages[index];
                      final isLatest = index == chatState.messages.length - 1;
                      return MessageBubble(
                        key: ValueKey(msg.id),
                        message: msg,
                        isLatest: isLatest,
                      );
                    },
                  ),
          ),

          // Input bar
          ChatInput(
            isLoading: chatState.isLoading,
            onSend: (question) {
              chatNotifier.sendMessage(question);
            },
          ),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(
      BuildContext context, ChatNotifier notifier) {
    return AppBar(
      backgroundColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      leading: Builder(
        builder: (context) => IconButton(
          icon: const Icon(Icons.menu_rounded, color: AppTheme.textSecondary),
          tooltip: 'Menu Utama',
          onPressed: () => Scaffold.of(context).openDrawer(),
        ),
      ),
      title: null,
      actions: [
        Consumer(
          builder: (context, ref, child) {
            final voiceState = ref.watch(voiceProvider);
            return IconButton(
              icon: Icon(
                voiceState.isTtsEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded,
                color: voiceState.isTtsEnabled ? AppTheme.accentPrimary : AppTheme.textMuted,
              ),
              tooltip: voiceState.isTtsEnabled ? 'Matikan Suara Asisten' : 'Aktifkan Suara Asisten',
              onPressed: () {
                ref.read(voiceProvider.notifier).toggleTts(!voiceState.isTtsEnabled);
              },
            );
          },
        ),
        const SizedBox(width: 12),
      ],
    );
  }

  void _showClearDialog(BuildContext context, ChatNotifier notifier) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surfaceCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: AppTheme.surfaceBorder),
        ),
        title: const Text('Hapus Percakapan',
            style: TextStyle(color: AppTheme.textPrimary)),
        content: const Text(
          'Semua pesan akan dihapus. Lanjutkan?',
          style: TextStyle(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Batal',
                style: TextStyle(color: AppTheme.textMuted)),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              notifier.clearChat();
            },
            child: const Text('Hapus',
                style: TextStyle(color: AppTheme.errorColor)),
          ),
        ],
      ),
    );
  }
}

// ── Empty State ─────────────────────────────────────────────
class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              gradient: AppTheme.accentGradient,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: AppTheme.accentPrimary.withValues(alpha: 0.3),
                  blurRadius: 24,
                ),
              ],
            ),
            child: const Icon(Icons.auto_stories_rounded,
                color: Colors.white, size: 36),
          ).animate().scale(duration: 500.ms, curve: Curves.elasticOut),
          const SizedBox(height: 20),
          Text(
            'Pedoman Akademik',
            style: Theme.of(context).textTheme.titleLarge,
          ).animate().fadeIn(delay: 200.ms),
          const SizedBox(height: 8),
          Text(
            'Tanyakan apa saja tentang aturan\ndan prosedur akademik kampus',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium,
          ).animate().fadeIn(delay: 300.ms),
        ],
      ),
    );
  }
}
