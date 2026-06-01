// ============================================================
// core/theme/app_theme.dart
// Design system — warna, tipografi, komponen theme
// Dark mode premium dengan aksen biru/indigo
// ============================================================

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  AppTheme._();

  // ── Color Palette ──────────────────────────────────────────
  static const Color backgroundDark = Color(0xFF0D0F14);
  static const Color surfaceDark = Color(0xFF161B27);
  static const Color surfaceCard = Color(0xFF1E2433);
  static const Color surfaceBorder = Color(0xFF2A3042);

  static const Color accentPrimary = Color(0xFF6366F1);   // Indigo
  static const Color accentSecondary = Color(0xFF818CF8);  // Light Indigo
  static const Color accentTertiary = Color(0xFF34D399);   // Emerald (similarity)

  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF475569);

  static const Color userBubble = Color(0xFF4F46E5);       // User message
  static const Color aiBubble = Color(0xFF1E2433);         // AI message

  static const Color errorColor = Color(0xFFEF4444);
  static const Color successColor = Color(0xFF10B981);
  static const Color warningColor = Color(0xFFF59E0B);

  // ── Gradients ──────────────────────────────────────────────
  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0D0F14),
      Color(0xFF111827),
    ],
  );

  static const LinearGradient accentGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [accentPrimary, Color(0xFF8B5CF6)],
  );

  static const LinearGradient userBubbleGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF4F46E5), Color(0xFF7C3AED)],
  );

  // ── Typography ─────────────────────────────────────────────
  static TextTheme get _textTheme => GoogleFonts.interTextTheme(
        const TextTheme(
          displayLarge: TextStyle(
            fontSize: 32, fontWeight: FontWeight.w700,
            color: textPrimary, letterSpacing: -0.5,
          ),
          displayMedium: TextStyle(
            fontSize: 24, fontWeight: FontWeight.w700,
            color: textPrimary, letterSpacing: -0.3,
          ),
          titleLarge: TextStyle(
            fontSize: 18, fontWeight: FontWeight.w600,
            color: textPrimary, letterSpacing: -0.2,
          ),
          titleMedium: TextStyle(
            fontSize: 16, fontWeight: FontWeight.w500,
            color: textPrimary,
          ),
          bodyLarge: TextStyle(
            fontSize: 15, fontWeight: FontWeight.w400,
            color: textPrimary, height: 1.6,
          ),
          bodyMedium: TextStyle(
            fontSize: 14, fontWeight: FontWeight.w400,
            color: textSecondary, height: 1.5,
          ),
          bodySmall: TextStyle(
            fontSize: 12, fontWeight: FontWeight.w400,
            color: textMuted,
          ),
          labelLarge: TextStyle(
            fontSize: 14, fontWeight: FontWeight.w600,
            color: textPrimary, letterSpacing: 0.1,
          ),
        ),
      );

  // ── Dark Theme ─────────────────────────────────────────────
  static ThemeData get dark => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        textTheme: _textTheme,
        colorScheme: const ColorScheme.dark(
          primary: accentPrimary,
          secondary: accentSecondary,
          surface: surfaceDark,
          error: errorColor,
          onPrimary: Colors.white,
          onSecondary: Colors.white,
          onSurface: textPrimary,
          outline: surfaceBorder,
        ),
        scaffoldBackgroundColor: backgroundDark,
        appBarTheme: AppBarTheme(
          backgroundColor: backgroundDark,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: GoogleFonts.inter(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: textPrimary,
          ),
          iconTheme: const IconThemeData(color: textSecondary),
        ),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: surfaceDark,
          indicatorColor: accentPrimary.withOpacity(0.2),
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w600, color: accentSecondary);
            }
            return GoogleFonts.inter(fontSize: 11, color: textMuted);
          }),
          iconTheme: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const IconThemeData(color: accentSecondary, size: 22);
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
          hintStyle: GoogleFonts.inter(color: textMuted, fontSize: 14),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
        dividerTheme: const DividerThemeData(
          color: surfaceBorder,
          thickness: 1,
        ),
      );
}
