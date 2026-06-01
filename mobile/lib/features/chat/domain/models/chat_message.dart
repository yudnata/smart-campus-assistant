// ============================================================
// features/chat/domain/models/chat_message.dart
// Model satu pesan di percakapan chat
// ============================================================

import 'package:equatable/equatable.dart';
import 'source_chunk.dart';

enum MessageRole { user, assistant }

enum MessageStatus { sending, success, error }

class ChatMessage extends Equatable {
  final String id;
  final MessageRole role;
  final String content;
  final List<SourceChunk> sources;
  final MessageStatus status;
  final DateTime createdAt;

  const ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    this.sources = const [],
    this.status = MessageStatus.success,
    required this.createdAt,
  });

  bool get isUser => role == MessageRole.user;
  bool get isAssistant => role == MessageRole.assistant;
  bool get isSending => status == MessageStatus.sending;
  bool get hasError => status == MessageStatus.error;
  bool get hasSources => sources.isNotEmpty;

  ChatMessage copyWith({
    String? content,
    List<SourceChunk>? sources,
    MessageStatus? status,
  }) {
    return ChatMessage(
      id: id,
      role: role,
      content: content ?? this.content,
      sources: sources ?? this.sources,
      status: status ?? this.status,
      createdAt: createdAt,
    );
  }

  /// Buat pesan user baru
  factory ChatMessage.user(String content) => ChatMessage(
        id: DateTime.now().microsecondsSinceEpoch.toString(),
        role: MessageRole.user,
        content: content,
        status: MessageStatus.success,
        createdAt: DateTime.now(),
      );

  /// Buat placeholder "loading" untuk AI
  factory ChatMessage.assistantLoading() => ChatMessage(
        id: '${DateTime.now().microsecondsSinceEpoch}_ai',
        role: MessageRole.assistant,
        content: '',
        status: MessageStatus.sending,
        createdAt: DateTime.now(),
      );

  /// Buat pesan error
  factory ChatMessage.error(String message) => ChatMessage(
        id: '${DateTime.now().microsecondsSinceEpoch}_err',
        role: MessageRole.assistant,
        content: message,
        status: MessageStatus.error,
        createdAt: DateTime.now(),
      );

  @override
  List<Object?> get props => [id, role, content, sources, status];
}
