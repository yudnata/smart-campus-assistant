// ============================================================
// features/chat/domain/repositories/chat_repository.dart
// Abstract repository — domain layer tidak tahu implementasinya
// ============================================================

import 'package:fpdart/fpdart.dart';
import '../../../../core/error/failures.dart';
import '../models/source_chunk.dart';
import '../models/retrieval_stats.dart';

/// Response lengkap dari satu query RAG
class ChatQueryResult {
  final String answer;
  final List<SourceChunk> sources;
  final RetrievalStats stats;

  const ChatQueryResult({
    required this.answer,
    required this.sources,
    required this.stats,
  });
}

/// Abstract repository — diimplementasi di data layer
abstract class ChatRepository {
  /// Kirim pertanyaan ke backend RAG
  /// Return Either<Failure, ChatQueryResult>
  Future<Either<Failure, ChatQueryResult>> sendMessage({
    required String question,
    int topK = 5,
  });
}
