// ============================================================
// features/chat/presentation/widgets/chat_input.dart
// Input bar dengan tombol kirim dan animasi focus
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../../../core/theme/app_theme.dart';
import '../providers/voice_provider.dart';
import 'full_speech_overlay.dart';

class ChatInput extends ConsumerStatefulWidget {
  final bool isLoading;
  final ValueChanged<String> onSend;

  const ChatInput({
    super.key,
    required this.isLoading,
    required this.onSend,
  });

  @override
  ConsumerState<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends ConsumerState<ChatInput> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  bool _hasText = false;
  bool _isFocused = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      setState(() => _hasText = _controller.text.trim().isNotEmpty);
    });
    _focusNode.addListener(() {
      setState(() => _isFocused = _focusNode.hasFocus);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _handleSend() {
    final text = _controller.text.trim();
    if (text.isEmpty || widget.isLoading) return;
    widget.onSend(text);
    _controller.clear();
  }

  void _showFullSpeechOverlay(BuildContext context) {
    showGeneralDialog(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 300),
      pageBuilder: (context, anim1, anim2) {
        return FullSpeechOverlay(
          onSend: (text) {
            widget.onSend(text);
          },
        );
      },
      transitionBuilder: (context, anim1, anim2, child) {
        return FadeTransition(
          opacity: anim1,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.9, end: 1.0).animate(
              CurvedAnimation(parent: anim1, curve: Curves.easeOutCubic),
            ),
            child: child,
          ),
        );
      },
    );
  }

  void _showSiriOverlay(BuildContext context) {
    final voiceNotifier = ref.read(voiceProvider.notifier);

    // Start listening immediately when the sheet opens
    voiceNotifier.startListening((text) {
      // Callback for real-time speech results
    });

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      isScrollControlled: true,
      constraints: const BoxConstraints(maxWidth: double.infinity),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
      ),
      builder: (context) {
        return Consumer(
          builder: (context, ref, child) {
            final voiceState = ref.watch(voiceProvider);

            return Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
              height: 280,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Pull bar
                  Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceBorder,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    voiceState.isListening
                        ? 'Mendengarkan...'
                        : 'Selesai Mendengar',
                    style: const TextStyle(
                      fontFamily: 'Quicksand',
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    voiceState.lastSpokenWords.isEmpty
                        ? 'Katakan sesuatu tentang pedoman akademik'
                        : voiceState.lastSpokenWords,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: 'Quicksand',
                      fontSize: 14,
                      fontWeight: voiceState.lastSpokenWords.isEmpty
                          ? FontWeight.normal
                          : FontWeight.w600,
                      color: voiceState.lastSpokenWords.isEmpty
                          ? AppTheme.textSecondary
                          : AppTheme.accentPrimary,
                    ),
                  ),
                  const Spacer(),
                  // Siri voice wave animation
                  if (voiceState.isListening)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(5, (index) {
                        return AnimatedContainer(
                          duration: Duration(milliseconds: 150 + (index * 50)),
                          width: 8,
                          height: 30 + (index % 2 == 0 ? 20.0 : 40.0),
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [
                                AppTheme.accentPrimary,
                                AppTheme.accentSecondary,
                                Color(0xFF38BDF8),
                              ],
                            ),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        )
                            .animate(
                                onPlay: (controller) =>
                                    controller.repeat(reverse: true))
                            .scaleY(
                              begin: 0.3,
                              end: 1.5,
                              duration:
                                  Duration(milliseconds: 300 + (index * 100)),
                              curve: Curves.easeInOut,
                            );
                      }),
                    )
                  else
                    const Icon(Icons.check_circle_rounded,
                        color: Colors.green, size: 48),
                  const Spacer(),
                  // Cancel / Tap to finish
                  TextButton(
                    onPressed: () {
                      final text = ref.read(voiceProvider).lastSpokenWords;
                      voiceNotifier.stopListening();
                      Navigator.pop(context);

                      if (text.trim().isNotEmpty) {
                        widget.onSend(text.trim());
                      }
                    },
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 24, vertical: 12),
                      backgroundColor:
                          AppTheme.accentPrimary.withValues(alpha: 0.1),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                    child: const Text(
                      'Selesai Bicara',
                      style: TextStyle(
                        fontFamily: 'Quicksand',
                        fontWeight: FontWeight.w600,
                        color: AppTheme.accentPrimary,
                      ),
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    ).then((_) {
      // Ensure listening stops if the bottom sheet is dismissed by dragging down
      voiceNotifier.stopListening();
    });
  }

  @override
  Widget build(BuildContext context) {
    final bottomPadding = MediaQuery.of(context).padding.bottom;
    return Container(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 8,
        bottom: bottomPadding > 0 ? bottomPadding + 8 : 16,
      ),
      decoration: const BoxDecoration(
        color: Colors.transparent,
      ),
      child: Row(
        children: [
          // Voice Assistant Mode Button (Full Speech Mode)
          GestureDetector(
            onTap: () => _showFullSpeechOverlay(context),
            child: Container(
              width: 52,
              height: 52,
              decoration: const BoxDecoration(
                gradient: AppTheme.accentGradient,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Color(0x224F46E5),
                    blurRadius: 8,
                    offset: Offset(0, 3),
                  ),
                ],
              ),
              child: const Icon(Icons.auto_awesome_rounded,
                  color: Colors.white, size: 26),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: AppTheme.surfaceCard,
                borderRadius: BorderRadius.circular(32),
                border: Border.all(
                  color: _isFocused
                      ? AppTheme.accentPrimary.withValues(alpha: 0.6)
                      : AppTheme.surfaceBorder,
                  width: _isFocused ? 1.5 : 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: _isFocused
                        ? AppTheme.accentPrimary.withValues(alpha: 0.15)
                        : Colors.black.withValues(alpha: 0.08),
                    blurRadius: 20,
                    spreadRadius: 0,
                    offset: const Offset(0, 6),
                  )
                ],
              ),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              child: Row(
                children: [
                  // Text field
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      focusNode: _focusNode,
                      enabled: true,
                      maxLines: 4,
                      minLines: 1,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _handleSend(),
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                            color: AppTheme.textPrimary,
                          ),
                      decoration: InputDecoration(
                        filled: false,
                        hintText: 'Tanya...',
                        hintStyle: const TextStyle(
                          color: AppTheme.textMuted,
                          fontSize: 14,
                        ),
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 16,
                        ),
                      ),
                    ),
                  ),

                  // Mic Button
                  IconButton(
                    icon: const Icon(Icons.mic_none_rounded,
                        color: AppTheme.accentPrimary),
                    tooltip: 'Bicara',
                    onPressed: () {
                      _showSiriOverlay(context);
                    },
                  ),

                  const SizedBox(width: 4),

                  AnimatedScale(
                    scale: (_hasText || widget.isLoading) ? 1.0 : 0.9,
                    duration: 150.ms,
                    child: IconButton(
                      icon: Icon(
                        Icons.send_rounded,
                        color: (_hasText && !widget.isLoading)
                            ? AppTheme.accentPrimary
                            : AppTheme.textMuted,
                      ),
                      onPressed:
                          (widget.isLoading || !_hasText) ? null : _handleSend,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
