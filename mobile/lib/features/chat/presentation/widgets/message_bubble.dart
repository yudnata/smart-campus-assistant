// ============================================================
// features/chat/presentation/widgets/message_bubble.dart
// Bubble pesan user & AI dengan animasi
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../domain/models/chat_message.dart';
import '../../../../core/theme/app_theme.dart';
import '../providers/voice_provider.dart';
import 'source_panel.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;
  final bool isLatest;

  const MessageBubble({
    super.key,
    required this.message,
    this.isLatest = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Column(
        crossAxisAlignment:
            message.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // Role label
          Padding(
            padding: const EdgeInsets.only(bottom: 4, left: 4, right: 4),
            child: Text(
              message.isUser ? 'Kamu' : '🎓 Asisten Akademik',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppTheme.textMuted,
                    fontWeight: FontWeight.w500,
                  ),
            ),
          ),

          // Bubble konten
          _buildBubble(context),

          // Sumber referensi (hanya untuk pesan AI yang punya sources)
          if (message.isAssistant && message.hasSources) ...[
            const SizedBox(height: 8),
            SourcePanel(sources: message.sources),
          ],
        ],
      ),
    )
        .animate(
            // Animasi masuk untuk pesan baru
            )
        .fadeIn(duration: 300.ms)
        .slideY(
          begin: 0.1,
          end: 0,
          duration: 300.ms,
          curve: Curves.easeOutCubic,
        );
  }

  Widget _buildBubble(BuildContext context) {
    if (message.isSending) return _LoadingBubble();
    if (message.hasError) return _ErrorBubble(message: message.content);

    return message.isUser
        ? _UserBubble(content: message.content)
        : _AiBubble(content: message.content);
  }
}

// ── User Bubble ─────────────────────────────────────────────
class _UserBubble extends StatelessWidget {
  final String content;
  const _UserBubble({required this.content});

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(
        maxWidth: MediaQuery.of(context).size.width * 0.78,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        gradient: AppTheme.userBubbleGradient,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(20),
          topRight: Radius.circular(20),
          bottomLeft: Radius.circular(20),
          bottomRight: Radius.circular(4),
        ),
        boxShadow: [
          BoxShadow(
            color: Color(0x334F46E5),
            blurRadius: 12,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Text(
        content,
        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: Colors.white,
              height: 1.5,
            ),
      ),
    );
  }
}

// ── AI Bubble ───────────────────────────────────────────────
class _AiBubble extends ConsumerWidget {
  final String content;
  const _AiBubble({required this.content});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final voiceState = ref.watch(voiceProvider);
    final isSpeaking = voiceState.isSpeaking;

    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Container(
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.76,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: AppTheme.surfaceCard,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(4),
              topRight: Radius.circular(20),
              bottomLeft: Radius.circular(20),
              bottomRight: Radius.circular(20),
            ),
            border: Border.all(color: AppTheme.surfaceBorder, width: 1),
          ),
          child: Text(
            content,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: AppTheme.textPrimary,
                  height: 1.65,
                ),
          ),
        ),
        const SizedBox(width: 4),
        IconButton(
          icon: Icon(
            isSpeaking ? Icons.volume_off_rounded : Icons.volume_up_rounded,
            color: isSpeaking ? AppTheme.accentPrimary : AppTheme.textMuted,
            size: 18,
          ),
          padding: EdgeInsets.zero,
          constraints: const BoxConstraints(),
          onPressed: () {
            if (isSpeaking) {
              ref.read(voiceProvider.notifier).stopSpeaking();
            } else {
              ref.read(voiceProvider.notifier).speak(content);
            }
          },
          tooltip: isSpeaking ? 'Hentikan Suara' : 'Dengarkan',
        ),
      ],
    );
  }
}

// ── Loading Bubble ──────────────────────────────────────────
class _LoadingBubble extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceCard,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(4),
          topRight: Radius.circular(20),
          bottomLeft: Radius.circular(20),
          bottomRight: Radius.circular(20),
        ),
        border: Border.all(color: AppTheme.surfaceBorder),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Mencari di pedoman akademik',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppTheme.textMuted,
                  fontStyle: FontStyle.italic,
                ),
          ),
          const SizedBox(width: 8),
          _TypingDots(),
        ],
      ),
    );
  }
}

class _TypingDots extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: List.generate(3, (i) {
        return Container(
          width: 5,
          height: 5,
          margin: const EdgeInsets.symmetric(horizontal: 2),
          decoration: const BoxDecoration(
            color: AppTheme.accentPrimary,
            shape: BoxShape.circle,
          ),
        )
            .animate(onPlay: (c) => c.repeat())
            .fadeIn(delay: (i * 200).ms, duration: 400.ms)
            .then()
            .fadeOut(duration: 400.ms);
      }),
    );
  }
}

// ── Error Bubble ────────────────────────────────────────────
class _ErrorBubble extends StatelessWidget {
  final String message;
  const _ErrorBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.errorColor.withValues(alpha: 0.1),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(4),
          topRight: Radius.circular(20),
          bottomLeft: Radius.circular(20),
          bottomRight: Radius.circular(20),
        ),
        border: Border.all(color: AppTheme.errorColor.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline_rounded,
              color: AppTheme.errorColor, size: 16),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppTheme.errorColor,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
