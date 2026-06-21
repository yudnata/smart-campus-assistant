// ============================================================
// core/constants/api_constants.dart
// Semua URL dan endpoint API backend Express.js
// ============================================================

import 'package:flutter/foundation.dart';

class ApiConstants {
  ApiConstants._(); // prevent instantiation

  // Membaca Base URL dari environment variable (--dart-define=API_URL=...)
  // Dengan fallback ke localhost untuk Web dan 10.0.2.2 untuk Android Emulator
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: kIsWeb ? 'http://localhost:3001' : 'http://10.0.2.2:3001',
  );

  // ── Endpoints ──────────────────────────────────────────────
  static const String chat = '$baseUrl/api/chat';
  static const String stats = '$baseUrl/api/stats';
  static const String health = '$baseUrl/health';

  // ── Timeouts ───────────────────────────────────────────────
  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 60); // LLM bisa lambat
  static const Duration sendTimeout = Duration(seconds: 30);
}
