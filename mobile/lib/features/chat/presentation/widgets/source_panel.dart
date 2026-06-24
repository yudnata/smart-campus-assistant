// ============================================================
// features/chat/presentation/widgets/source_panel.dart
// Panel sumber referensi — menampilkan chunks dari pgvector
// Tap kartu → bottom sheet detail lengkap
// ============================================================

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
        // ── Toggle button ──────────────────────────────────────
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

        // ── Source cards (expandable) ──────────────────────────
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

// ── Source Card (tappable) ───────────────────────────────────
class _SourceCard extends StatefulWidget {
  final SourceChunk chunk;
  final int index;

  const _SourceCard({required this.chunk, required this.index});

  @override
  State<_SourceCard> createState() => _SourceCardState();
}

class _SourceCardState extends State<_SourceCard> {
  bool _pressed = false;

  Color get _relevanceColor {
    if (widget.chunk.similarity >= 0.85) return AppTheme.accentTertiary;
    if (widget.chunk.similarity >= 0.70) return AppTheme.accentSecondary;
    if (widget.chunk.similarity >= 0.50) return AppTheme.warningColor;
    return AppTheme.textMuted;
  }

  void _openDetail() {
    HapticFeedback.lightImpact();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _SourceDetailSheet(
        chunk: widget.chunk,
        index: widget.index,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        _openDetail();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.97 : 1.0,
        duration: 120.ms,
        child: Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: _pressed
                ? AppTheme.accentPrimary.withValues(alpha: 0.04)
                : AppTheme.backgroundLight,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _pressed
                  ? AppTheme.accentPrimary.withValues(alpha: 0.4)
                  : AppTheme.surfaceBorder,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Header: nomor + halaman + similarity + tap hint ──
              Row(
                children: [
                  Container(
                    width: 20,
                    height: 20,
                    decoration: BoxDecoration(
                      color: AppTheme.accentPrimary.withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      '${widget.index}',
                      style: const TextStyle(
                        fontSize: 10,
                        color: AppTheme.accentSecondary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.menu_book_rounded,
                      size: 12, color: AppTheme.textMuted),
                  const SizedBox(width: 4),
                  Text(
                    'Hal. ${widget.chunk.page}',
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppTheme.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const Spacer(),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: _relevanceColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                          color: _relevanceColor.withValues(alpha: 0.3)),
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
                          '${widget.chunk.similarityPercent.toStringAsFixed(0)}%',
                          style: TextStyle(
                            fontSize: 10,
                            color: _relevanceColor,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Icon(Icons.open_in_new_rounded,
                      size: 12, color: AppTheme.textMuted),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                widget.chunk.preview,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppTheme.textMuted,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  const Icon(Icons.touch_app_rounded,
                      size: 10, color: AppTheme.accentSecondary),
                  const SizedBox(width: 3),
                  Text(
                    'Ketuk untuk melihat detail',
                    style: TextStyle(
                      fontSize: 10,
                      color: AppTheme.accentSecondary.withValues(alpha: 0.7),
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    ).animate().fadeIn(delay: 50.ms).slideY(begin: 0.05, end: 0);
  }
}

// ── Source Detail Bottom Sheet ───────────────────────────────
class _SourceDetailSheet extends StatelessWidget {
  final SourceChunk chunk;
  final int index;

  const _SourceDetailSheet({required this.chunk, required this.index});

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.65,
      minChildSize: 0.4,
      maxChildSize: 0.92,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: AppTheme.surfaceLight,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              // ── Drag handle ────────────────────────────────────
              Padding(
                padding: const EdgeInsets.only(top: 12, bottom: 4),
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceBorder,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),

              // ── Header sheet ───────────────────────────────────
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 12, 0),
                child: Row(
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      decoration: const BoxDecoration(
                        gradient: AppTheme.accentGradient,
                        shape: BoxShape.circle,
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        '$index',
                        style: const TextStyle(
                          fontSize: 13,
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Detail Sumber Referensi',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.textPrimary,
                            fontFamily: 'Quicksand',
                          ),
                        ),
                        Text(
                          'Halaman ${chunk.page}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppTheme.textMuted,
                            fontFamily: 'Quicksand',
                          ),
                        ),
                      ],
                    ),
                    const Spacer(),
                    IconButton(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close_rounded,
                          color: AppTheme.textMuted, size: 20),
                    ),
                  ],
                ),
              ),

              const Divider(height: 20, indent: 20, endIndent: 20),

              // ── Scrollable content ─────────────────────────────
              Expanded(
                child: ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
                  children: [
                    _RelevanceCard(chunk: chunk),
                    const SizedBox(height: 16),
                    _MetadataRow(chunk: chunk),
                    const SizedBox(height: 16),
                    _FullTextCard(chunk: chunk),
                    const SizedBox(height: 16),
                    _ValidityVerdict(chunk: chunk),
                  ],
                ),
              ),
            ],
          ),
        )
            .animate()
            .slideY(
                begin: 0.1,
                end: 0,
                duration: 300.ms,
                curve: Curves.easeOutCubic)
            .fadeIn(duration: 200.ms);
      },
    );
  }
}

// ── Relevance Card ───────────────────────────────────────────
class _RelevanceCard extends StatelessWidget {
  final SourceChunk chunk;
  const _RelevanceCard({required this.chunk});

  Color get _color {
    if (chunk.similarity >= 0.85) return AppTheme.accentTertiary;
    if (chunk.similarity >= 0.70) return AppTheme.accentSecondary;
    if (chunk.similarity >= 0.50) return AppTheme.warningColor;
    return AppTheme.textMuted;
  }

  IconData get _icon {
    if (chunk.similarity >= 0.85) return Icons.verified_rounded;
    if (chunk.similarity >= 0.70) return Icons.check_circle_outline_rounded;
    if (chunk.similarity >= 0.50) return Icons.info_outline_rounded;
    return Icons.help_outline_rounded;
  }

  @override
  Widget build(BuildContext context) {
    final percent = chunk.similarityPercent;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _color.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _color.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(_icon, size: 18, color: _color),
              const SizedBox(width: 8),
              Text(
                chunk.relevanceLabel,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: _color,
                  fontFamily: 'Quicksand',
                ),
              ),
              const Spacer(),
              Text(
                '${percent.toStringAsFixed(1)}%',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: _color,
                  fontFamily: 'Quicksand',
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: chunk.similarity,
              minHeight: 7,
              backgroundColor: _color.withValues(alpha: 0.15),
              valueColor: AlwaysStoppedAnimation<Color>(_color),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Skor kemiripan semantik antara pertanyaan dan isi dokumen.',
            style: TextStyle(
              fontSize: 11,
              color: _color.withValues(alpha: 0.7),
              fontFamily: 'Quicksand',
            ),
          ),
        ],
      ),
    );
  }
}

// ── Metadata Row ─────────────────────────────────────────────
class _MetadataRow extends StatelessWidget {
  final SourceChunk chunk;
  const _MetadataRow({required this.chunk});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _MetaChip(
            icon: Icons.menu_book_rounded,
            label: 'Halaman',
            value: '${chunk.page}',
            color: AppTheme.accentPrimary,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _MetaChip(
            icon: Icons.bar_chart_rounded,
            label: 'Skor',
            value: chunk.similarity.toStringAsFixed(4),
            color: AppTheme.accentSecondary,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _MetaChip(
            icon: Icons.source_rounded,
            label: 'Tipe',
            value: 'PDF',
            color: AppTheme.warningColor,
          ),
        ),
      ],
    );
  }
}

class _MetaChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _MetaChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              color: color.withValues(alpha: 0.7),
              fontFamily: 'Quicksand',
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: color,
              fontFamily: 'Quicksand',
            ),
          ),
        ],
      ),
    );
  }
}

// ── Full Text Card ────────────────────────────────────────────
class _FullTextCard extends StatefulWidget {
  final SourceChunk chunk;
  const _FullTextCard({required this.chunk});

  @override
  State<_FullTextCard> createState() => _FullTextCardState();
}

class _FullTextCardState extends State<_FullTextCard> {
  bool _copied = false;

  void _copyText() async {
    await Clipboard.setData(ClipboardData(text: widget.chunk.preview));
    setState(() => _copied = true);
    HapticFeedback.mediumImpact();
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) setState(() => _copied = false);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.backgroundLight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.article_outlined,
                  size: 16, color: AppTheme.accentPrimary),
              const SizedBox(width: 8),
              const Text(
                'Isi Teks Sumber',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                  fontFamily: 'Quicksand',
                ),
              ),
              const Spacer(),
              GestureDetector(
                onTap: _copyText,
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: _copied
                      ? const Row(
                          key: ValueKey('copied'),
                          children: [
                            Icon(Icons.check_rounded,
                                size: 14, color: AppTheme.accentTertiary),
                            SizedBox(width: 4),
                            Text(
                              'Disalin!',
                              style: TextStyle(
                                fontSize: 11,
                                color: AppTheme.accentTertiary,
                                fontWeight: FontWeight.w600,
                                fontFamily: 'Quicksand',
                              ),
                            ),
                          ],
                        )
                      : const Row(
                          key: ValueKey('copy'),
                          children: [
                            Icon(Icons.copy_outlined,
                                size: 14, color: AppTheme.textMuted),
                            SizedBox(width: 4),
                            Text(
                              'Salin',
                              style: TextStyle(
                                fontSize: 11,
                                color: AppTheme.textMuted,
                                fontFamily: 'Quicksand',
                              ),
                            ),
                          ],
                        ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SelectableText(
            widget.chunk.preview.isEmpty
                ? '(Konten tidak tersedia)'
                : widget.chunk.preview,
            style: const TextStyle(
              fontSize: 13,
              color: AppTheme.textSecondary,
              height: 1.7,
              fontFamily: 'Quicksand',
            ),
          ),
        ],
      ),
    );
  }
}

// ── Validity Verdict ─────────────────────────────────────────
class _ValidityVerdict extends StatelessWidget {
  final SourceChunk chunk;
  const _ValidityVerdict({required this.chunk});

  @override
  Widget build(BuildContext context) {
    final isValid = chunk.similarity >= 0.50;
    final color = isValid ? AppTheme.accentTertiary : AppTheme.warningColor;
    final icon = isValid ? Icons.shield_rounded : Icons.warning_amber_rounded;
    final title = isValid ? 'Data Valid' : 'Relevansi Rendah';
    final desc = isValid
        ? 'Sumber ini memiliki kemiripan semantik yang cukup tinggi dengan pertanyaan Anda, sehingga dianggap sebagai referensi yang relevan.'
        : 'Skor kemiripan sumber ini rendah. Informasi mungkin kurang relevan dengan konteks pertanyaan.';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 22, color: color),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: color,
                    fontFamily: 'Quicksand',
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  desc,
                  style: TextStyle(
                    fontSize: 12,
                    color: color.withValues(alpha: 0.8),
                    height: 1.5,
                    fontFamily: 'Quicksand',
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
