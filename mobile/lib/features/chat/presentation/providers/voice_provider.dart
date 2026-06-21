import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';

class VoiceState {
  final bool isListening;
  final String lastSpokenWords;
  final bool isSpeaking;
  final bool isTtsEnabled;
  final bool isSttAvailable;

  VoiceState({
    this.isListening = false,
    this.lastSpokenWords = '',
    this.isSpeaking = false,
    this.isTtsEnabled = true, // Aktifkan TTS otomatis secara default
    this.isSttAvailable = false,
  });

  VoiceState copyWith({
    bool? isListening,
    String? lastSpokenWords,
    bool? isSpeaking,
    bool? isTtsEnabled,
    bool? isSttAvailable,
  }) {
    return VoiceState(
      isListening: isListening ?? this.isListening,
      lastSpokenWords: lastSpokenWords ?? this.lastSpokenWords,
      isSpeaking: isSpeaking ?? this.isSpeaking,
      isTtsEnabled: isTtsEnabled ?? this.isTtsEnabled,
      isSttAvailable: isSttAvailable ?? this.isSttAvailable,
    );
  }
}

class VoiceNotifier extends StateNotifier<VoiceState> {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _tts = FlutterTts();

  VoiceNotifier() : super(VoiceState()) {
    _initSpeech();
    _initTts();
  }

  Future<void> _initSpeech() async {
    try {
      bool available = await _speech.initialize(
        onError: (val) => stopListening(),
        onStatus: (val) {
          if (val == 'notListening' || val == 'done') {
            state = state.copyWith(isListening: false);
          }
        },
      );
      state = state.copyWith(isSttAvailable: available);
    } catch (e) {
      state = state.copyWith(isSttAvailable: false);
    }
  }

  Future<void> _initTts() async {
    try {
      // Coba set language ke id-ID (standar) atau id_ID (beberapa device Android)
      var result = await _tts.setLanguage("id-ID");
      if (result == 0) {
        await _tts.setLanguage("id_ID");
      }
      
      await _tts.setPitch(1.0);
      await _tts.setSpeechRate(1.0); // Dipercepat menjadi ~2.0x sesuai permintaan user

      _tts.setStartHandler(() {
        state = state.copyWith(isSpeaking: true);
      });

      _tts.setCompletionHandler(() {
        state = state.copyWith(isSpeaking: false);
      });

      _tts.setErrorHandler((msg) {
        state = state.copyWith(isSpeaking: false);
      });
    } catch (_) {}
  }

  // ── Speech-To-Text (STT) ───────────────────────────────────

  Future<void> startListening(Function(String) onResultText) async {
    if (!state.isSttAvailable) {
      // Re-init jika sebelumnya gagal
      await _initSpeech();
    }

    if (state.isSttAvailable && !state.isListening) {
      // Stop TTS jika sedang bersuara agar tidak saling mengganggu
      if (state.isSpeaking) {
        await stopSpeaking();
      }

      state = state.copyWith(isListening: true, lastSpokenWords: '');
      
      await _speech.listen(
        onResult: (val) {
          state = state.copyWith(lastSpokenWords: val.recognizedWords);
          onResultText(val.recognizedWords);
        },
        listenOptions: stt.SpeechListenOptions(
          localeId: 'id_ID', // Paksa menggunakan Bahasa Indonesia
          listenFor: const Duration(seconds: 30),
          pauseFor: const Duration(seconds: 5),
        ),
      );
    }
  }

  Future<void> stopListening() async {
    if (state.isListening) {
      await _speech.stop();
      state = state.copyWith(isListening: false);
    }
  }

  // ── Text-To-Speech (TTS) ───────────────────────────────────

  Future<void> speak(String text) async {
    if (!state.isTtsEnabled) return;

    // Bersihkan format markdown sederhana dari teks jawaban sebelum dibaca
    final cleanText = text
        .replaceAll(RegExp(r'\*|_|`|#'), '') // Hapus markdown symbols
        .replaceAll(RegExp(r'\[.*?\]\(.*?\)|file:\/\/.*? '), '') // Hapus link
        .trim();

    if (cleanText.isNotEmpty) {
      if (state.isListening) {
        await stopListening();
      }
      await _tts.speak(cleanText);
    }
  }

  Future<void> stopSpeaking() async {
    if (state.isSpeaking) {
      await _tts.stop();
      state = state.copyWith(isSpeaking: false);
    }
  }

  void toggleTts(bool enabled) {
    state = state.copyWith(isTtsEnabled: enabled);
    if (!enabled) {
      stopSpeaking();
    }
  }
}

final voiceProvider = StateNotifierProvider<VoiceNotifier, VoiceState>((ref) {
  return VoiceNotifier();
});
