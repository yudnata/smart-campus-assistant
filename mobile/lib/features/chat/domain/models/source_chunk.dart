// ============================================================
// features/chat/domain/models/source_chunk.dart
// Model untuk satu chunk hasil retrieval dari pgvector
// ============================================================

import 'package:equatable/equatable.dart';

class SourceChunk extends Equatable {
  final int page;
  final double similarity;
  final String preview;

  const SourceChunk({
    required this.page,
    required this.similarity,
    required this.preview,
  });

  factory SourceChunk.fromJson(Map<String, dynamic> json) {
    return SourceChunk(
      page: (json['page'] as num).toInt(),
      similarity: (json['similarity'] as num).toDouble(),
      preview: json['preview'] as String,
    );
  }

  /// Similarity sebagai persentase (0-100)
  double get similarityPercent => similarity * 100;

  /// Label relevansi untuk UI
  String get relevanceLabel {
    if (similarity >= 0.85) return 'Sangat Relevan';
    if (similarity >= 0.7) return 'Relevan';
    if (similarity >= 0.5) return 'Cukup Relevan';
    return 'Kurang Relevan';
  }

  @override
  List<Object?> get props => [page, similarity, preview];
}
