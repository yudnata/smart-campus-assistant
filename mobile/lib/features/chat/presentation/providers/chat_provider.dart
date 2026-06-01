// ============================================================
// features/chat/presentation/providers/chat_provider.dart
// Riverpod state management untuk chat
// ============================================================

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/chat_remote_datasource.dart';
import '../../data/repositories/chat_repository_impl.dart';
import '../../domain/models/chat_message.dart';
import '../../domain/repositories/chat_repository.dart';

// ── Dependency Providers ────────────────────────────────────

final chatDataSourceProvider = Provider<ChatRemoteDataSource>(
  (ref) => ChatRemoteDataSource(),
);

final chatRepositoryProvider = Provider<ChatRepository>(
  (ref) => ChatRepositoryImpl(ref.watch(chatDataSourceProvider)),
);

// ── Chat State ──────────────────────────────────────────────

class ChatState {
  final List<ChatMessage> messages;
  final bool isLoading;
  final String? errorMessage;

  const ChatState({
    this.messages = const [],
    this.isLoading = false,
    this.errorMessage,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isLoading,
    String? errorMessage,
    bool clearError = false,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

// ── Chat Notifier ───────────────────────────────────────────

class ChatNotifier extends Notifier<ChatState> {
  @override
  ChatState build() {
    final welcomeMsg = ChatMessage(
      id: 'welcome',
      role: MessageRole.assistant,
      content:
          'Halo! 👋 Saya asisten pedoman akademik kampus.\n\nTanyakan apa saja tentang:\n• Pengambilan SKS dan KRS\n• Prosedur cuti akademik\n• Syarat kelulusan\n• Beasiswa dan persyaratannya\n• Dan topik akademik lainnya',
      createdAt: DateTime(2024),
    );
    return ChatState(messages: [welcomeMsg]);
  }

  ChatRepository get _repo => ref.read(chatRepositoryProvider);

  Future<void> sendMessage(String question) async {
    if (question.trim().isEmpty || state.isLoading) return;

    final userMsg = ChatMessage.user(question.trim());
    final loadingMsg = ChatMessage.assistantLoading();

    // Tambah pesan user + loading indicator
    state = state.copyWith(
      messages: [...state.messages, userMsg, loadingMsg],
      isLoading: true,
      clearError: true,
    );

    // Panggil repository
    final result = await _repo.sendMessage(question: question.trim());

    result.fold(
      // Failure — ganti loading dengan pesan error
      (failure) {
        final errorMsg = ChatMessage.error(failure.message);
        final updatedMessages = List<ChatMessage>.from(state.messages)
          ..removeLast() // hapus loading
          ..add(errorMsg);

        state = state.copyWith(
          messages: updatedMessages,
          isLoading: false,
          errorMessage: failure.message,
        );
      },
      // Success — ganti loading dengan jawaban
      (result) {
        final aiMsg = loadingMsg.copyWith(
          content: result.answer,
          sources: result.sources,
          status: MessageStatus.success,
        );
        final updatedMessages = List<ChatMessage>.from(state.messages)
          ..removeLast() // hapus loading
          ..add(aiMsg);

        state = state.copyWith(
          messages: updatedMessages,
          isLoading: false,
        );
      },
    );
  }

  void clearChat() {
    state = build(); // reset ke initial state
  }
}

// Provider utama yang digunakan di UI
final chatProvider = NotifierProvider<ChatNotifier, ChatState>(
  ChatNotifier.new,
);
