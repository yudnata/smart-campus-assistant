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
    // Mulai mendengarkan secara otomatis saat overlay dibuka
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(voiceProvider.notifier).startListening((text) {
        setState(() => _tempWords = text);
      });
    });
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
    
    // Listen status voice & chat untuk membuat dialog melingkar (auto-loop)
    ref.listen(voiceProvider, (prev, next) {
      // 1. Jika selesai berbicara (isListening berubah dari true ke false), kirim otomatis
      if (prev?.isListening == true && next.isListening == false) {
        final finalSpeech = next.lastSpokenWords.trim();
        if (finalSpeech.isNotEmpty && !ref.read(chatProvider).isLoading) {
          widget.onSend(finalSpeech);
          setState(() => _tempWords = '');
        }
      }

      // 2. Jika asisten selesai membacakan teks (isSpeaking berubah dari true ke false),
      // otomatis aktifkan kembali mikrofon agar user bisa langsung berbicara lagi
      if (prev?.isSpeaking == true && next.isSpeaking == false) {
        Future.delayed(const Duration(milliseconds: 600), () {
          if (mounted && 
              !ref.read(voiceProvider).isListening && 
              !ref.read(chatProvider).isLoading) {
            ref.read(voiceProvider.notifier).startListening((text) {
              setState(() => _tempWords = text);
            });
          }
        });
      }
    });

    // Bacakan balasan RAG otomatis hanya saat sedang berada di dalam overlay Mode Suara
    ref.listen(chatProvider, (prev, next) {
      if (next.messages.isNotEmpty) {
        final lastMsg = next.messages.last;
        final prevLastMsg = prev?.messages.isNotEmpty == true ? prev!.messages.last : null;
        
        if (lastMsg.isAssistant && 
            lastMsg.status == MessageStatus.success && 
            (prevLastMsg == null || prevLastMsg.status == MessageStatus.sending || prevLastMsg.id != lastMsg.id)) {
          ref.read(voiceProvider.notifier).speak(lastMsg.content);
        }
      }
    });

    // Menentukan Status Utama untuk UI
    String statusTitle = 'Asisten Siap';
    String statusSub = 'Katakan sesuatu...';
    Widget centerWidget = const SizedBox();

    if (chatState.isLoading) {
      statusTitle = 'Memikirkan Jawaban';
      statusSub = 'Mencari informasi di pedoman akademik...';
      centerWidget = _buildProcessingOrb();
    } else if (voiceState.isSpeaking) {
      statusTitle = 'Asisten Berbicara';
      statusSub = 'Mendengarkan jawaban...';
      centerWidget = _buildSpeakingOrb();
    } else if (voiceState.isListening) {
      statusTitle = 'Mendengarkan';
      statusSub = _tempWords.isEmpty ? 'Katakan pertanyaan Anda...' : _tempWords;
      centerWidget = _buildListeningOrb();
    } else {
      centerWidget = _buildIdleOrb();
    }

    return Scaffold(
      backgroundColor: Colors.black.withValues(alpha: 0.95), // Premium dark mode background
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
                      Icon(Icons.spatial_audio_rounded, color: AppTheme.accentPrimary, size: 24),
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
                    icon: const Icon(Icons.close_rounded, color: Colors.white70, size: 28),
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
                    fontSize: 15,
                    color: Colors.white70,
                    height: 1.5,
                  ),
                ),
              ),
              const SizedBox(height: 48),

              // Bottom control button (Manual Tap to Speak / Mute)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  GestureDetector(
                    onTap: () {
                      if (voiceState.isListening) {
                        ref.read(voiceProvider.notifier).stopListening();
                      } else if (voiceState.isSpeaking) {
                        ref.read(voiceProvider.notifier).stopSpeaking();
                      } else if (!chatState.isLoading) {
                        ref.read(voiceProvider.notifier).startListening((text) {
                          setState(() => _tempWords = text);
                        });
                      }
                    },
                    child: Container(
                      width: 72,
                      height: 72,
                      decoration: BoxDecoration(
                        gradient: AppTheme.accentGradient,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.accentPrimary.withValues(alpha: 0.4),
                            blurRadius: 20,
                            spreadRadius: 2,
                          ),
                        ],
                      ),
                      child: Icon(
                        voiceState.isListening
                            ? Icons.mic_rounded
                            : (voiceState.isSpeaking ? Icons.volume_up_rounded : Icons.mic_none_rounded),
                        color: Colors.white,
                        size: 32,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              const Text(
                'Percakapan berjalan dua arah secara otomatis.\nTekan tombol di atas untuk jeda.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontFamily: 'Quicksand',
                  fontSize: 12,
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
        ).animate(onPlay: (c) => c.repeat(reverse: true))
         .scale(begin: const Offset(0.8, 0.8), end: const Offset(1.2, 1.2), duration: 1200.ms, curve: Curves.easeInOut),
        
        // Wave outer layer 1
        Container(
          width: 170,
          height: 170,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppTheme.accentSecondary.withValues(alpha: 0.1),
          ),
        ).animate(onPlay: (c) => c.repeat(reverse: true))
         .scale(begin: const Offset(0.9, 0.9), end: const Offset(1.15, 1.15), duration: 800.ms, curve: Curves.easeInOut),

        // Glowing center orb
        Container(
          width: 120,
          height: 120,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            gradient: AppTheme.accentGradient,
          ),
          child: const Icon(Icons.mic_rounded, color: Colors.white, size: 48),
        ).animate(onPlay: (c) => c.repeat(reverse: true))
         .boxShadow(
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
            ).animate(onPlay: (c) => c.repeat(reverse: true))
             .scaleY(begin: 0.4, end: 1.6, duration: Duration(milliseconds: 250 + (index * 80)));
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
        border: Border.all(color: AppTheme.accentPrimary.withValues(alpha: 0.2), width: 4),
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
    ).animate(onPlay: (c) => c.repeat())
     .rotate(duration: 2000.ms);
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
      child: const Icon(Icons.spatial_audio_off_rounded, color: Colors.white54, size: 48),
    );
  }
}
