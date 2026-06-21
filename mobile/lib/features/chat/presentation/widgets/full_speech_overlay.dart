import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../providers/chat_provider.dart';
import '../providers/voice_provider.dart';
import '../../domain/models/chat_message.dart';
import '../../../../core/theme/app_theme.dart';

class FullSpeechOverlay extends ConsumerStatefulWidget {
  final ValueChanged<String> onSend;

  const FullSpeechOverlay({
    super.key,
    required this.onSend,
  });

  @override
  ConsumerState<FullSpeechOverlay> createState() => _FullSpeechOverlayState();
}

class _FullSpeechOverlayState extends ConsumerState<FullSpeechOverlay> {
  String _tempWords = '';
  late VoiceNotifier _voiceNotifier;

  @override
  void initState() {
    super.initState();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _voiceNotifier = ref.read(voiceProvider.notifier);
  }

  @override
  void dispose() {
    // Matikan mic dan suara saat keluar overlay
    _voiceNotifier.stopListening();
    _voiceNotifier.stopSpeaking();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final voiceState = ref.watch(voiceProvider);
    final chatState = ref.watch(chatProvider);

    // ── Dialog Loop Listener ─────────────────────────────────

    // Listen status voice untuk mendeteksi kapan tombol dilepas (selesai mendengar)
    ref.listen(voiceProvider, (prev, next) {
      // Jika selesai berbicara (isListening berubah dari true ke false), kirim otomatis hasil rekaman
      if (prev?.isListening == true && next.isListening == false) {
        final finalSpeech = next.lastSpokenWords.trim();
        if (finalSpeech.isNotEmpty && !ref.read(chatProvider).isLoading) {
          widget.onSend(finalSpeech);
          setState(() => _tempWords = '');
        }
      }
    });

    // Bacakan balasan RAG otomatis hanya saat sedang berada di dalam overlay Mode Suara
    ref.listen(chatProvider, (prev, next) {
      if (next.messages.isNotEmpty) {
        final lastMsg = next.messages.last;
        final prevLastMsg =
            prev?.messages.isNotEmpty == true ? prev!.messages.last : null;

        if (lastMsg.isAssistant &&
            lastMsg.status == MessageStatus.success &&
            (prevLastMsg == null ||
                prevLastMsg.status == MessageStatus.sending ||
                prevLastMsg.id != lastMsg.id)) {
          ref.read(voiceProvider.notifier).speak(lastMsg.content);
        }
      }
    });

    // Menentukan Status Utama untuk UI
    String statusTitle = 'Asisten Suara';
    String statusSub = 'Tekan & tahan tombol di bawah untuk mulai berbicara';
    String bottomHint = 'Tahan untuk bicara, lepas untuk mengirim';
    Widget centerWidget = const SizedBox();

    if (chatState.isLoading) {
      statusTitle = 'Memikirkan Jawaban';
      statusSub = 'Mencari informasi di pedoman akademik...';
      bottomHint = 'Mohon tunggu sebentar...';
      centerWidget = _buildProcessingOrb();
    } else if (voiceState.isSpeaking) {
      statusTitle = 'Asisten Berbicara';
      statusSub = 'Mendengarkan jawaban...';
      bottomHint = 'Tahan tombol di bawah untuk memotong & bertanya baru';
      centerWidget = _buildSpeakingOrb();
    } else if (voiceState.isListening) {
      statusTitle = 'Mendengarkan';
      statusSub =
          _tempWords.isEmpty ? 'Lepas tombol untuk mengirim...' : _tempWords;
      bottomHint = 'Lepas tombol jika sudah selesai berbicara';
      centerWidget = _buildListeningOrb();
    } else {
      centerWidget = _buildIdleOrb();
    }

    return Scaffold(
      backgroundColor:
          Colors.black.withValues(alpha: 0.95), // Premium dark mode background
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            children: [
              // Header area
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.spatial_audio_rounded,
                          color: AppTheme.accentPrimary, size: 24),
                      SizedBox(width: 10),
                      Text(
                        'Mode Suara Asisten',
                        style: TextStyle(
                          fontFamily: 'Quicksand',
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close_rounded,
                        color: Colors.white70, size: 28),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const Spacer(),

              // Center Visualizer Orb
              Center(child: centerWidget),

              const Spacer(),

              // Status Teks
              Text(
                statusTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontFamily: 'Quicksand',
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 12),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Text(
                  statusSub,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontFamily: 'Quicksand',
                    fontSize: 19,
                    fontWeight: FontWeight.w500,
                    color: Color(0xE6FFFFFF), // 90% opacity white constant
                    height: 1.5,
                  ),
                ),
              ),
              const SizedBox(height: 48),

              // Bottom control button (Hold to Talk / Release to Send)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  GestureDetector(
                    onTapDown: (_) {
                      // Hentikan asisten jika sedang berbicara saat user ingin mulai bertanya
                      if (voiceState.isSpeaking) {
                        ref.read(voiceProvider.notifier).stopSpeaking();
                      }
                      if (!chatState.isLoading) {
                        ref.read(voiceProvider.notifier).startListening((text) {
                          setState(() => _tempWords = text);
                        });
                      }
                    },
                    onTapUp: (_) {
                      if (voiceState.isListening) {
                        ref.read(voiceProvider.notifier).stopListening();
                      }
                    },
                    onTapCancel: () {
                      if (voiceState.isListening) {
                        ref.read(voiceProvider.notifier).stopListening();
                      }
                    },
                    child: Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        gradient: AppTheme.accentGradient,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.accentPrimary.withValues(
                                alpha: voiceState.isListening ? 0.6 : 0.3),
                            blurRadius: voiceState.isListening ? 30 : 15,
                            spreadRadius: voiceState.isListening ? 4 : 1,
                          ),
                        ],
                      ),
                      child: Icon(
                        voiceState.isListening
                            ? Icons.mic_rounded
                            : (voiceState.isSpeaking
                                ? Icons.volume_up_rounded
                                : Icons.mic_none_rounded),
                        color: Colors.white,
                        size: 36,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text(
                bottomHint,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontFamily: 'Quicksand',
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: Colors.white38,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Visualizer Orbs ───────────────────────────────────────

  Widget _buildListeningOrb() {
    return Stack(
      alignment: Alignment.center,
      children: [
        // Wave outer layer 2
        Container(
          width: 220,
          height: 220,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppTheme.accentPrimary.withValues(alpha: 0.05),
          ),
        ).animate(onPlay: (c) => c.repeat(reverse: true)).scale(
            begin: const Offset(0.8, 0.8),
            end: const Offset(1.2, 1.2),
            duration: 1200.ms,
            curve: Curves.easeInOut),

        // Wave outer layer 1
        Container(
          width: 170,
          height: 170,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppTheme.accentSecondary.withValues(alpha: 0.1),
          ),
        ).animate(onPlay: (c) => c.repeat(reverse: true)).scale(
            begin: const Offset(0.9, 0.9),
            end: const Offset(1.15, 1.15),
            duration: 800.ms,
            curve: Curves.easeInOut),

        // Glowing center orb
        Container(
          width: 120,
          height: 120,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            gradient: AppTheme.accentGradient,
          ),
          child: const Icon(Icons.mic_rounded, color: Colors.white, size: 48),
        ).animate(onPlay: (c) => c.repeat(reverse: true)).boxShadow(
              begin: const BoxShadow(color: Color(0x334F46E5), blurRadius: 10),
              end: const BoxShadow(color: Color(0xAA4F46E5), blurRadius: 40),
              duration: 1000.ms,
            ),
      ],
    );
  }

  Widget _buildSpeakingOrb() {
    return Stack(
      alignment: Alignment.center,
      children: [
        // Pulsing audio waves representation
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(5, (index) {
            return AnimatedContainer(
              duration: Duration(milliseconds: 100 + (index * 60)),
              width: 10,
              height: 40 + (index % 2 == 0 ? 30.0 : 60.0),
              margin: const EdgeInsets.symmetric(horizontal: 6),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    AppTheme.accentPrimary,
                    Color(0xFF38BDF8),
                  ],
                ),
                borderRadius: BorderRadius.circular(5),
              ),
            ).animate(onPlay: (c) => c.repeat(reverse: true)).scaleY(
                begin: 0.4,
                end: 1.6,
                duration: Duration(milliseconds: 250 + (index * 80)));
          }),
        ),
      ],
    );
  }

  Widget _buildProcessingOrb() {
    return Container(
      width: 120,
      height: 120,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(
            color: AppTheme.accentPrimary.withValues(alpha: 0.2), width: 4),
      ),
      child: const Center(
        child: SizedBox(
          width: 90,
          height: 90,
          child: CircularProgressIndicator(
            strokeWidth: 4,
            valueColor: AlwaysStoppedAnimation<Color>(AppTheme.accentPrimary),
          ),
        ),
      ),
    ).animate(onPlay: (c) => c.repeat()).rotate(duration: 2000.ms);
  }

  Widget _buildIdleOrb() {
    return Container(
      width: 120,
      height: 120,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white10,
        border: Border.all(color: Colors.white24, width: 2),
      ),
      child: const Icon(Icons.spatial_audio_off_rounded,
          color: Colors.white54, size: 48),
    );
  }
}
