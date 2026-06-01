// ============================================================
// core/constants/api_constants.dart
// Semua URL dan endpoint API backend Express.js
// ============================================================

class ApiConstants {
  ApiConstants._(); // prevent instantiation

  // Ganti dengan IP lokal mesin kamu saat development
  // Android emulator: 10.0.2.2
  // iOS Simulator: localhost atau 127.0.0.1
  // Device fisik: IP LAN mesin backend (cek dengan `ipconfig`)
  static const String _baseUrl = 'http://10.0.2.2:3001';

  // ── Endpoints ──────────────────────────────────────────────
  static const String chat = '$_baseUrl/api/chat';
  static const String stats = '$_baseUrl/api/stats';
  static const String health = '$_baseUrl/health';

  // ── Timeouts ───────────────────────────────────────────────
  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 60); // LLM bisa lambat
  static const Duration sendTimeout = Duration(seconds: 30);
}
