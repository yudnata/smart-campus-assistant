// ============================================================
// core/theme/app_theme.dart
// Design system — warna, tipografi, komponen theme
// Light mode premium dengan aksen Indigo/Slate (White Mode)
// ============================================================

import 'package:flutter/material.dart';

class AppTheme {
  AppTheme._();

  // ── Color Palette (Light/White Mode) ─────────────────────────
  static const Color backgroundLight =
      Color(0xFFF8FAFC); // Soft slate background
  static const Color surfaceLight = Color(0xFFFFFFFF); // Pure white surface
  static const Color surfaceCard = Color(0xFFFFFFFF); // Cards/bubbles use white
  static const Color surfaceBorder = Color(0xFFE2E8F0); // Light slate border

  static const Color accentPrimary = Color(0xFF4F46E5); // Indigo-600
  static const Color accentSecondary = Color(0xFF6366F1); // Indigo-500
  static const Color accentTertiary = Color(0xFF10B981); // Emerald (similarity)

  static const Color textPrimary =
      Color(0xFF0F172A); // Slate-900 (High contrast)
  static const Color textSecondary = Color(0xFF475569); // Slate-600
  static const Color textMuted = Color(0xFF94A3B8); // Slate-400

  static const Color errorColor = Color(0xFFEF4444);
  static const Color successColor = Color(0xFF10B981);
  static const Color warningColor = Color(0xFFF59E0B);

  // ── Gradients ──────────────────────────────────────────────
  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFFF8FAFC),
      Color(0xFFF1F5F9),
    ],
  );

  static const LinearGradient accentGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [accentPrimary, Color(0xFF7C3AED)],
  );

  static const LinearGradient userBubbleGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF4F46E5), Color(0xFF6366F1)],
  );

  // ── Typography ─────────────────────────────────────────────
  static TextTheme get _textTheme => const TextTheme(
        displayLarge: TextStyle(
          fontFamily: 'Quicksand',
          fontSize: 32,
          fontWeight: FontWeight.w700,
          color: textPrimary,
          letterSpacing: -0.5,
        ),
        displayMedium: TextStyle(
          fontFamily: 'Quicksand',
          fontSize: 24,
          fontWeight: FontWeight.w700,
          color: textPrimary,
          letterSpacing: -0.3,
        ),
        titleLarge: TextStyle(
          fontFamily: 'Quicksand',
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: textPrimary,
          letterSpacing: -0.2,
        ),
        titleMedium: TextStyle(
          fontFamily: 'Quicksand',
          fontSize: 16,
          fontWeight: FontWeight.w500,
          color: textPrimary,
        ),
        bodyLarge: TextStyle(
          fontFamily: 'Quicksand',
          fontSize: 15,
          fontWeight: FontWeight.w400,
          color: textPrimary,
          height: 1.6,
        ),
        bodyMedium: TextStyle(
          fontFamily: 'Quicksand',
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: textSecondary,
          height: 1.5,
        ),
        bodySmall: TextStyle(
          fontFamily: 'Quicksand',
          fontSize: 12,
          fontWeight: FontWeight.w400,
          color: textMuted,
        ),
        labelLarge: TextStyle(
          fontFamily: 'Quicksand',
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: textPrimary,
          letterSpacing: 0.1,
        ),
      );

  // ── Light Theme ─────────────────────────────────────────────
  static ThemeData get light => ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        fontFamily: 'Quicksand',
        textTheme: _textTheme,
        colorScheme: const ColorScheme.light(
          primary: accentPrimary,
          secondary: accentSecondary,
          surface: surfaceLight,
          error: errorColor,
          onPrimary: Colors.white,
          onSecondary: Colors.white,
          onSurface: textPrimary,
          outline: surfaceBorder,
        ),
        scaffoldBackgroundColor: backgroundLight,
        appBarTheme: const AppBarTheme(
          backgroundColor: surfaceLight,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: TextStyle(
            fontFamily: 'Quicksand',
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: textPrimary,
          ),
          iconTheme: IconThemeData(color: textSecondary),
        ),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: surfaceLight,
          indicatorColor: accentPrimary.withValues(alpha: 0.1),
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const TextStyle(
                  fontFamily: 'Quicksand',
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: accentPrimary);
            }
            return const TextStyle(
                fontFamily: 'Quicksand', fontSize: 11, color: textMuted);
          }),
          iconTheme: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const IconThemeData(color: accentPrimary, size: 22);
            }
            return const IconThemeData(color: textMuted, size: 22);
          }),
        ),
        cardTheme: CardThemeData(
          color: surfaceCard,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: surfaceBorder, width: 1),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: surfaceCard,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: surfaceBorder),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: surfaceBorder),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: accentPrimary, width: 1.5),
          ),
          hintStyle: const TextStyle(
              fontFamily: 'Quicksand', color: textMuted, fontSize: 14),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
        dividerTheme: const DividerThemeData(
          color: surfaceBorder,
          thickness: 1,
        ),
      );

  // Keep dark getter for compatibility/fallback but route it to light
  static ThemeData get dark => light;
}
