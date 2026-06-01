// ============================================================
// features/chat/domain/models/retrieval_stats.dart
// Statistik retrieval untuk keperluan evaluasi STKI
// ============================================================

import 'package:equatable/equatable.dart';

class RetrievalStats extends Equatable {
  final int retrievalTimeMs;
  final int chunksFound;
  final double topSimilarity;
  final double avgSimilarity;

  const RetrievalStats({
    required this.retrievalTimeMs,
    required this.chunksFound,
    required this.topSimilarity,
    required this.avgSimilarity,
  });

  factory RetrievalStats.fromJson(Map<String, dynamic> json) {
    return RetrievalStats(
      retrievalTimeMs: (json['retrievalTimeMs'] as num).toInt(),
      chunksFound: (json['chunksFound'] as num).toInt(),
      topSimilarity: (json['topSimilarity'] as num).toDouble(),
      avgSimilarity: (json['avgSimilarity'] as num).toDouble(),
    );
  }

  @override
  List<Object?> get props =>
      [retrievalTimeMs, chunksFound, topSimilarity, avgSimilarity];
}
