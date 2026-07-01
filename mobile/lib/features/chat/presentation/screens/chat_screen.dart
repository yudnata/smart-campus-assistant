// ============================================================
// features/chat/presentation/screens/chat_screen.dart
// Main chat screen — menggabungkan semua widget chat
// ============================================================

import 'dart:async';
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
  final Map<String, GlobalKey> _messageKeys = {};
  bool _isNavigatorExpanded = false;
  double _navigatorOpacity = 1.0;
  Timer? _navigatorIdleTimer;

  @override
  void initState() {
    super.initState();
    _resetNavigatorIdleTimer();
  }

  @override
  void dispose() {
    _navigatorIdleTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _resetNavigatorIdleTimer() {
    _navigatorIdleTimer?.cancel();
    if (mounted) {
      setState(() {
        _navigatorOpacity = 1.0;
      });
    }

    // Hanya jalankan timer jika navigator sedang tertutup (collapsed)
    if (!_isNavigatorExpanded) {
      _navigatorIdleTimer = Timer(const Duration(seconds: 3), () {
        if (mounted && !_isNavigatorExpanded) {
          setState(() {
            _navigatorOpacity =
                0.70; // Opacity sedang (redup tapi tetap terlihat) saat idle
          });
        }
      });
    }
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

  void _scrollToMessage(String msgId) {
    final key = _messageKeys[msgId];
    if (key != null && key.currentContext != null) {
      Scrollable.ensureVisible(
        key.currentContext!,
        duration: const Duration(milliseconds: 500),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatProvider);
    final chatNotifier = ref.read(chatProvider.notifier);

    // Bersihkan keys jika obrolan dihapus/kosong
    if (chatState.messages.isEmpty) {
      _messageKeys.clear();
    }

    // Scroll ke bawah saat pesan baru masuk atau proses loading asisten selesai
    ref.listen(chatProvider, (prev, next) {
      if (next.messages.isNotEmpty) {
        if (prev?.messages.length != next.messages.length ||
            (prev?.isLoading == true && next.isLoading == false)) {
          _scrollToBottom();
          _resetNavigatorIdleTimer(); // Reset timer & nyalakan opacity kembali ke 1.0!
          // Delay kecil untuk memastikan layout teks panjang asisten sudah selesai di-render
          Future.delayed(const Duration(milliseconds: 100), _scrollToBottom);
          Future.delayed(const Duration(milliseconds: 300), _scrollToBottom);
        }
      }
    });

    return Scaffold(
      backgroundColor: AppTheme.backgroundLight,
      appBar: _buildAppBar(context, chatNotifier),
      drawer: const ChatDrawer(),
      body: Stack(
        children: [
          Column(
            children: [
              // Pesan list
              Expanded(
                child: chatState.messages.isEmpty
                    ? _EmptyState()
                    : ListView.builder(
                        controller: _scrollController,
                        cacheExtent: 99999,
                        padding: const EdgeInsets.only(top: 12, bottom: 8),
                        itemCount: chatState.messages.length,
                        itemBuilder: (context, index) {
                          final msg = chatState.messages[index];
                          final isLatest =
                              index == chatState.messages.length - 1;

                          if (msg.isUser) {
                            _messageKeys.putIfAbsent(msg.id, () => GlobalKey());
                          }

                          return MessageBubble(
                            key: msg.isUser
                                ? _messageKeys[msg.id]
                                : ValueKey(msg.id),
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

          // Floating Checkpoint Navigator (DeepSeek style)
          _buildCheckpointNavigator(chatState.messages),
        ],
      ),
    );
  }

  Widget _buildCheckpointNavigator(List<ChatMessage> messages) {
    final userPrompts = messages.where((m) => m.isUser).toList();
    // Hanya tampilkan jika pengguna memiliki minimal 2 pertanyaan untuk navigasi
    if (userPrompts.length <= 1) return const SizedBox();

    final double sidebarWidth = 190.0;
    final double handleWidth = 32.0;

    return AnimatedPositioned(
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOutCubic,
      right: _isNavigatorExpanded ? 0 : -sidebarWidth,
      width: sidebarWidth +
          handleWidth, // Tentukan lebar total secara statis agar layout & hit testing stabil di Android
      top: MediaQuery.of(context).size.height *
          0.25, // Posisikan melayang di tengah vertikal layar
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 300),
        opacity: _isNavigatorExpanded ? 1.0 : _navigatorOpacity,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Handle / Tombol panah untuk buka tutup panel (desain tab light mode premium dengan hit target besar)
            GestureDetector(
              onTap: () {
                setState(() {
                  _isNavigatorExpanded = !_isNavigatorExpanded;
                  _resetNavigatorIdleTimer();
                });
              },
              child: Container(
                width: handleWidth,
                height: 72,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(16),
                    bottomLeft: Radius.circular(16),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.08),
                      blurRadius: 10,
                      spreadRadius: 1,
                      offset: const Offset(-2, 0),
                    ),
                  ],
                  border: Border.all(color: AppTheme.surfaceBorder, width: 1.5),
                ),
                child: Icon(
                  _isNavigatorExpanded
                      ? Icons.chevron_right_rounded
                      : Icons.chevron_left_rounded,
                  color: AppTheme.accentPrimary,
                  size: 24,
                ),
              ),
            ),

            // Konten Checkpoints Sidebar (Light Mode)
            Container(
              width: sidebarWidth,
              constraints: const BoxConstraints(maxHeight: 320),
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.08),
                    blurRadius: 12,
                    spreadRadius: 1,
                    offset: const Offset(-4, 4),
                  ),
                ],
                border: Border.all(color: AppTheme.surfaceBorder, width: 1.5),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                ),
              ),
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(left: 8.0, bottom: 8.0),
                    child: Row(
                      children: [
                        const Icon(Icons.bookmarks_rounded,
                            size: 14, color: AppTheme.accentPrimary),
                        const SizedBox(width: 6),
                        Text(
                          'Checkpoint Tanya',
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    fontFamily: 'Quicksand',
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.textPrimary,
                                  ),
                        ),
                      ],
                    ),
                  ),
                  const Divider(height: 1, color: AppTheme.surfaceBorder),
                  const SizedBox(height: 6),
                  Flexible(
                    child: SingleChildScrollView(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: List.generate(userPrompts.length, (index) {
                          final prompt = userPrompts[index];

                          // Bersihkan spasi/line break, potong teks jika melebihi panjang display
                          final cleanPrompt =
                              prompt.content.trim().replaceAll('\n', ' ');
                          final displayPrompt = cleanPrompt.length > 18
                              ? '${cleanPrompt.substring(0, 18)}...'
                              : cleanPrompt;

                          return Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () {
                                _scrollToMessage(prompt.id);
                                _resetNavigatorIdleTimer();
                              },
                              borderRadius: BorderRadius.circular(8),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    vertical: 10.0, horizontal: 6.0),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      margin: const EdgeInsets.only(top: 2.0),
                                      width: 16,
                                      height: 16,
                                      decoration: const BoxDecoration(
                                        shape: BoxShape.circle,
                                        color: AppTheme.accentPrimary,
                                      ),
                                      child: Center(
                                        child: Text(
                                          '${index + 1}',
                                          style: const TextStyle(
                                            fontSize: 9,
                                            fontWeight: FontWeight.bold,
                                            color: Colors.white,
                                          ),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        displayPrompt,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontFamily: 'Quicksand',
                                          fontSize: 12,
                                          fontWeight: FontWeight.w500,
                                          color: AppTheme.textSecondary,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          );
                        }),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
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
                voiceState.isTtsEnabled
                    ? Icons.volume_up_rounded
                    : Icons.volume_off_rounded,
                color: voiceState.isTtsEnabled
                    ? AppTheme.accentPrimary
                    : AppTheme.textMuted,
              ),
              tooltip: voiceState.isTtsEnabled
                  ? 'Matikan Suara Asisten'
                  : 'Aktifkan Suara Asisten',
              onPressed: () {
                ref
                    .read(voiceProvider.notifier)
                    .toggleTts(!voiceState.isTtsEnabled);
              },
            );
          },
        ),
        const SizedBox(width: 12),
      ],
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
