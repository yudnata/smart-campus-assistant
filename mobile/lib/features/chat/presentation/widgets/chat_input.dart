// ============================================================
// features/chat/presentation/widgets/chat_input.dart
// Input bar dengan tombol kirim dan animasi focus
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../../../core/theme/app_theme.dart';

class ChatInput extends StatefulWidget {
  final bool isLoading;
  final ValueChanged<String> onSend;

  const ChatInput({
    super.key,
    required this.isLoading,
    required this.onSend,
  });

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput> {
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

  void _showSiriOverlay(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
      ),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Container(
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
                  const Text(
                    'Mendengarkan...',
                    style: TextStyle(
                      fontFamily: 'Quicksand',
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Katakan sesuatu tentang pedoman akademik',
                    style: TextStyle(
                      fontFamily: 'Quicksand',
                      fontSize: 13,
                      color: AppTheme.textSecondary,
                    ),
                  ),
                  const Spacer(),
                  // Siri voice wave animation mockup
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
                          .animate(onPlay: (controller) => controller.repeat(reverse: true))
                          .scaleY(
                            begin: 0.3,
                            end: 1.5,
                            duration: Duration(milliseconds: 300 + (index * 100)),
                            curve: Curves.easeInOut,
                          );
                    }),
                  ),
                  const Spacer(),
                  // Cancel / Tap to finish
                  TextButton(
                    onPressed: () {
                      Navigator.pop(context);
                      // Fill text with mockup question
                      setState(() {
                        _controller.text = 'Berapa syarat minimum kelulusan IPK?';
                      });
                    },
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                      backgroundColor: AppTheme.accentPrimary.withValues(alpha: 0.1),
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
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 12,
        bottom: MediaQuery.of(context).padding.bottom + 12,
      ),
      decoration: BoxDecoration(
        color: AppTheme.surfaceLight,
        border: Border(
          top: BorderSide(
            color: _isFocused
                ? AppTheme.accentPrimary.withValues(alpha: 0.4)
                : AppTheme.surfaceBorder,
          ),
        ),
      ),
      child: Row(
        children: [
          // Text field
          Expanded(
            child: AnimatedContainer(
              duration: 200.ms,
              decoration: BoxDecoration(
                color: AppTheme.surfaceCard,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: _isFocused
                      ? AppTheme.accentPrimary.withValues(alpha: 0.6)
                      : AppTheme.surfaceBorder,
                  width: _isFocused ? 1.5 : 1,
                ),
                boxShadow: _isFocused
                    ? [
                        BoxShadow(
                          color: AppTheme.accentPrimary.withValues(alpha: 0.1),
                          blurRadius: 12,
                          spreadRadius: 0,
                        )
                      ]
                    : null,
              ),
              child: TextField(
                controller: _controller,
                focusNode: _focusNode,
                enabled: !widget.isLoading,
                maxLines: 4,
                minLines: 1,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _handleSend(),
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: AppTheme.textPrimary,
                    ),
                decoration: InputDecoration(
                  filled: false,
                  hintText: widget.isLoading
                      ? 'Mencari jawaban...'
                      : 'Tanyakan tentang pedoman akademik...',
                  hintStyle: TextStyle(
                    color: widget.isLoading
                        ? AppTheme.accentPrimary.withValues(alpha: 0.5)
                        : AppTheme.textMuted,
                    fontSize: 14,
                  ),
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 18,
                    vertical: 12,
                  ),
                  suffixIcon: _hasText
                      ? null
                      : IconButton(
                          icon: const Icon(Icons.mic_none_rounded, color: AppTheme.accentPrimary),
                          onPressed: () {
                            _showSiriOverlay(context);
                          },
                        ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),

          // Send button
          AnimatedScale(
            scale: _hasText && !widget.isLoading ? 1.0 : 0.85,
            duration: 200.ms,
            curve: Curves.easeOutBack,
            child: GestureDetector(
              onTap: _handleSend,
              child: AnimatedContainer(
                duration: 200.ms,
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  gradient: _hasText && !widget.isLoading
                      ? AppTheme.accentGradient
                      : null,
                  color: _hasText && !widget.isLoading
                      ? null
                      : AppTheme.surfaceCard,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: _hasText && !widget.isLoading
                        ? Colors.transparent
                        : AppTheme.surfaceBorder,
                  ),
                  boxShadow: _hasText && !widget.isLoading
                      ? [
                          BoxShadow(
                            color:
                                AppTheme.accentPrimary.withValues(alpha: 0.35),
                            blurRadius: 12,
                            offset: const Offset(0, 4),
                          )
                        ]
                      : null,
                ),
                child: widget.isLoading
                    ? const Padding(
                        padding: EdgeInsets.all(14),
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppTheme.accentPrimary,
                        ),
                      )
                    : Icon(
                        Icons.send_rounded,
                        size: 20,
                        color: _hasText ? Colors.white : AppTheme.textMuted,
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
