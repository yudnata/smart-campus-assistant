// ============================================================
// features/chat/data/repositories/chat_repository_impl.dart
// Implementasi ChatRepository — translate DioException ke Failure
// ============================================================

import 'package:dio/dio.dart';
import 'package:fpdart/fpdart.dart';

import '../../../../core/error/failures.dart';
import '../../domain/models/source_chunk.dart';
import '../../domain/models/retrieval_stats.dart';
import '../../domain/repositories/chat_repository.dart';
import '../datasources/chat_remote_datasource.dart';

class ChatRepositoryImpl implements ChatRepository {
  final ChatRemoteDataSource _dataSource;

  const ChatRepositoryImpl(this._dataSource);

  Future<Either<Failure, ChatQueryResult>> sendMessage({
    required String question,
    int topK = 5,
    String? conversationId,
  }) async {
    try {
      final json = await _dataSource.sendMessage(
        question: question,
        topK: topK,
        conversationId: conversationId,
      );

      // Parse sources
      final rawSources = (json['sources'] as List<dynamic>? ?? []);
      final sources = rawSources
          .map((s) => SourceChunk.fromJson(s as Map<String, dynamic>))
          .toList();

      // Parse stats
      final rawStats = json['stats'] as Map<String, dynamic>? ?? {};
      final stats = rawStats.isNotEmpty
          ? RetrievalStats.fromJson(rawStats)
          : const RetrievalStats(
              retrievalTimeMs: 0,
              chunksFound: 0,
              topSimilarity: 0,
              avgSimilarity: 0,
            );

      return Right(
        ChatQueryResult(
          answer: json['answer'] as String,
          sources: sources,
          stats: stats,
        ),
      );
    } on DioException catch (e) {
      return Left(_mapDioError(e));
    } catch (e) {
      return Left(ParseFailure('Gagal memproses respons: $e'));
    }
  }

  Failure _mapDioError(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const TimeoutFailure();
      case DioExceptionType.connectionError:
        return const NetworkFailure();
      case DioExceptionType.badResponse:
        final status = e.response?.statusCode;
        final message = e.response?.data?['error'] as String? ??
            e.message ??
            'Server error';
        return ServerFailure(message, statusCode: status);
      default:
        return NetworkFailure(e.message ?? 'Koneksi gagal');
    }
  }
}
