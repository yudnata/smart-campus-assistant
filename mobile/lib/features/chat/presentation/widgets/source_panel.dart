// ============================================================
// features/chat/presentation/widgets/source_panel.dart
// Panel sumber referensi — menampilkan chunks dari pgvector
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../domain/models/source_chunk.dart';
import '../../../../core/theme/app_theme.dart';

class SourcePanel extends StatefulWidget {
  final List<SourceChunk> sources;
  const SourcePanel({super.key, required this.sources});

  @override
  State<SourcePanel> createState() => _SourcePanelState();
}

class _SourcePanelState extends State<SourcePanel> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Toggle button
        GestureDetector(
          onTap: () => setState(() => _expanded = !_expanded),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
            decoration: BoxDecoration(
              color: AppTheme.accentPrimary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: AppTheme.accentPrimary.withValues(alpha: 0.25),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.auto_stories_rounded,
                    size: 13, color: AppTheme.accentSecondary),
                const SizedBox(width: 6),
                Text(
                  '${widget.sources.length} sumber referensi',
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppTheme.accentSecondary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 4),
                AnimatedRotation(
                  turns: _expanded ? 0.5 : 0,
                  duration: 200.ms,
                  child: const Icon(Icons.expand_more_rounded,
                      size: 14, color: AppTheme.accentSecondary),
                ),
              ],
            ),
          ),
        ),

        // Source cards (expandable)
        AnimatedSize(
          duration: 250.ms,
          curve: Curves.easeOutCubic,
          child: _expanded
              ? Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Column(
                    children: widget.sources
                        .asMap()
                        .entries
                        .map((e) => _SourceCard(
                              chunk: e.value,
                              index: e.key + 1,
                            ))
                        .toList(),
                  ),
                )
              : const SizedBox.shrink(),
        ),
      ],
    );
  }
}

// ── Source Card ─────────────────────────────────────────────
class _SourceCard extends StatelessWidget {
  final SourceChunk chunk;
  final int index;

  const _SourceCard({required this.chunk, required this.index});

  Color get _relevanceColor {
    if (chunk.similarity >= 0.85) return AppTheme.accentTertiary;
    if (chunk.similarity >= 0.70) return AppTheme.accentSecondary;
    if (chunk.similarity >= 0.50) return AppTheme.warningColor;
    return AppTheme.textMuted;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.backgroundLight,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: nomor + halaman + similarity
          Row(
            children: [
              // Index badge
              Container(
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  color: AppTheme.accentPrimary.withValues(alpha: 0.2),
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: Text(
                  '$index',
                  style: const TextStyle(
                    fontSize: 10,
                    color: AppTheme.accentSecondary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              // Halaman
              const Icon(Icons.menu_book_rounded,
                  size: 12, color: AppTheme.textMuted),
              const SizedBox(width: 4),
              Text(
                'Halaman ${chunk.page}',
                style: const TextStyle(
                  fontSize: 11,
                  color: AppTheme.textSecondary,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const Spacer(),
              // Similarity badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _relevanceColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                  border:
                      Border.all(color: _relevanceColor.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 5,
                      height: 5,
                      decoration: BoxDecoration(
                        color: _relevanceColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${chunk.similarityPercent.toStringAsFixed(0)}%',
                      style: TextStyle(
                        fontSize: 10,
                        color: _relevanceColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          // Preview teks
          Text(
            chunk.preview,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 12,
              color: AppTheme.textMuted,
              height: 1.5,
            ),
          ),
        ],
      ),
    ).animate().fadeIn(delay: 50.ms).slideY(begin: 0.05, end: 0);
  }
}
