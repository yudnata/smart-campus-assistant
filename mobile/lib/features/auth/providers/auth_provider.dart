import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dio/dio.dart';
import '../../../core/constants/api_constants.dart';

// Dio instance untuk auth
final authDioProvider = Provider<Dio>((ref) {
  return Dio(BaseOptions(
    baseUrl: '${ApiConstants.baseUrl}/api',
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 10),
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'ngrok-skip-browser-warning': 'true',
    },
  ));
});

class AuthState {
  final bool isLoading;
  final bool isGuest;
  final bool isAuthenticated;
  final String? token;
  final Map<String, dynamic>? user;
  final String? error;

  AuthState({
    this.isLoading = false,
    this.isGuest = false,
    this.isAuthenticated = false,
    this.token,
    this.user,
    this.error,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isGuest,
    bool? isAuthenticated,
    String? token,
    Map<String, dynamic>? user,
    String? error,
    bool clearUser = false,
    bool clearToken = false,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isGuest: isGuest ?? this.isGuest,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      token: clearToken ? null : (token ?? this.token),
      user: clearUser ? null : (user ?? this.user),
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final Dio dio;

  AuthNotifier(this.dio) : super(AuthState(isLoading: true)) {
    _initAuth();
  }

  Future<void> _initAuth() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    
    if (token != null && token.isNotEmpty) {
      await _fetchMe(token);
    } else {
      state = state.copyWith(isLoading: false, isGuest: true); // Default ke guest jika tidak ada token
    }
  }

  Future<void> _fetchMe(String token) async {
    try {
      final response = await dio.get(
        '/auth/me',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
      state = state.copyWith(
        isLoading: false,
        isAuthenticated: true,
        isGuest: false,
        token: token,
        user: response.data,
      );
    } catch (e) {
      // ignore: avoid_print
      print('[AuthNotifier] _fetchMe failed: $e');
      if (e is DioException) {
        // ignore: avoid_print
        print('[AuthNotifier] _fetchMe DioException: ${e.response?.statusCode} - ${e.response?.data}');
      }
      final prefs = await SharedPreferences.getInstance();
      
      // Hanya hapus token jika server merespons dengan 401 (Unauthorized) atau 403 (Forbidden).
      // Jangan hapus jika hanya karena masalah koneksi internet/server offline.
      if (e is DioException && e.response != null && 
          (e.response!.statusCode == 401 || e.response!.statusCode == 403)) {
        await prefs.remove('auth_token');
        state = state.copyWith(isLoading: false, isGuest: true, isAuthenticated: false, clearToken: true, clearUser: true);
      } else {
        // Jika offline atau server down, tetap pertahankan status guest / error sementara tanpa menghapus token
        state = state.copyWith(isLoading: false, isGuest: true, error: "Gagal terhubung ke server.");
      }
    }
  }

  Future<bool> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await dio.post(
        '/auth/login',
        data: {'email': email, 'password': password},
      );
      final token = response.data['access_token'];
      
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', token);
      
      await _fetchMe(token);
      return true;
    } catch (e) {
      // ignore: avoid_print
      print('[AuthNotifier] login failed: $e');
      if (e is DioException) {
        // ignore: avoid_print
        print('[AuthNotifier] login DioException: ${e.response?.statusCode} - ${e.response?.data}');
      }
      String errorMessage = "Login gagal. Periksa kembali email & password Anda.";
      if (e is DioException && e.response != null) {
        errorMessage = e.response?.data['detail'] ?? errorMessage;
      }
      state = state.copyWith(isLoading: false, error: errorMessage);
      return false;
    }
  }

  Future<bool> register(String name, String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await dio.post(
        '/auth/register',
        data: {'name': name, 'email': email, 'password': password},
      );
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      String errorMessage = "Gagal mendaftar.";
      if (e is DioException && e.response != null) {
        errorMessage = e.response?.data['detail'] ?? errorMessage;
      }
      state = state.copyWith(isLoading: false, error: errorMessage);
      return false;
    }
  }

  Future<bool> verifyEmail(String email, String code) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await dio.post(
        '/auth/verify',
        data: {'email': email, 'code': code},
      );
      state = state.copyWith(isLoading: false);
      return true;
    } catch (e) {
      String errorMessage = "Kode verifikasi salah.";
      if (e is DioException && e.response != null) {
        errorMessage = e.response?.data['detail'] ?? errorMessage;
      }
      state = state.copyWith(isLoading: false, error: errorMessage);
      return false;
    }
  }

  void continueAsGuest() {
    state = state.copyWith(isGuest: true, isAuthenticated: false, clearToken: true, clearUser: true);
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    state = state.copyWith(isAuthenticated: false, clearToken: true, clearUser: true, isGuest: false);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.watch(authDioProvider));
});
