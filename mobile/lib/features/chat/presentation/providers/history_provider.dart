import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import '../../../auth/providers/auth_provider.dart';
import '../../domain/models/chat_message.dart';

class HistoryState {
  final bool isLoading;
  final List<Map<String, dynamic>> conversations;
  final String? error;
  final String? activeConversationId;

  HistoryState({
    this.isLoading = false,
    this.conversations = const [],
    this.error,
    this.activeConversationId,
  });

  HistoryState copyWith({
    bool? isLoading,
    List<Map<String, dynamic>>? conversations,
    String? error,
    String? activeConversationId,
  }) {
    return HistoryState(
      isLoading: isLoading ?? this.isLoading,
      conversations: conversations ?? this.conversations,
      error: error,
      activeConversationId: activeConversationId ?? this.activeConversationId,
    );
  }
}

class HistoryNotifier extends StateNotifier<HistoryState> {
  final Dio dio;
  final AuthState authState;

  HistoryNotifier(this.dio, this.authState) : super(HistoryState()) {
    if (authState.isAuthenticated) {
      fetchConversations();
    }
  }

  Future<void> fetchConversations() async {
    if (!authState.isAuthenticated || authState.token == null) return;
    
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await dio.get(
        '/chat/conversations',
        options: Options(headers: {'Authorization': 'Bearer ${authState.token}'}),
      );
      state = state.copyWith(
        isLoading: false,
        conversations: List<Map<String, dynamic>>.from(response.data),
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: 'Gagal memuat riwayat obrolan');
    }
  }

  Future<List<ChatMessage>> loadConversationMessages(String conversationId) async {
    if (!authState.isAuthenticated || authState.token == null) return [];
    
    try {
      final response = await dio.get(
        '/chat/conversations/$conversationId/messages',
        options: Options(headers: {'Authorization': 'Bearer ${authState.token}'}),
      );
      
      final messagesData = List<Map<String, dynamic>>.from(response.data);
      return messagesData.map((m) {
        if (m['role'] == 'user') {
          return ChatMessage(
            id: m['id'],
            role: MessageRole.user,
            content: m['content'],
            status: MessageStatus.success,
            createdAt: DateTime.parse(m['created_at']),
          );
        } else {
          return ChatMessage(
            id: m['id'],
            role: MessageRole.assistant,
            content: m['content'],
            status: MessageStatus.success,
            createdAt: DateTime.parse(m['created_at']),
          );
        }
      }).toList();
    } catch (e) {
      return [];
    }
  }

  Future<String?> createConversation(String title) async {
    if (!authState.isAuthenticated || authState.token == null) return null;
    
    try {
      final response = await dio.post(
        '/chat/conversations',
        data: {'title': title},
        options: Options(headers: {'Authorization': 'Bearer ${authState.token}'}),
      );
      final newConv = response.data;
      state = state.copyWith(
        conversations: [newConv, ...state.conversations],
        activeConversationId: newConv['id'],
      );
      return newConv['id'];
    } catch (e) {
      return null;
    }
  }

  void setActiveConversation(String? id) {
    state = state.copyWith(activeConversationId: id);
  }
}

final historyProvider = StateNotifierProvider<HistoryNotifier, HistoryState>((ref) {
  final dio = ref.watch(authDioProvider);
  final auth = ref.watch(authProvider);
  return HistoryNotifier(dio, auth);
});
